"""Folder scanning and quality classification.

Orchestrates the audit pipeline for image files: gathers filesystem facts,
anonymizes filenames, computes metrics, and classifies each image into a
QualityCategory. This module coordinates the other components (metrics,
anonymizer, config, models) but delegates the actual computation to them.

Classification is threshold-driven: metrics are compared against the values
in AuditorConfig. The scanner is resilient — a single unreadable file is
recorded as CORRUPTED rather than aborting the whole scan.
"""

from __future__ import annotations

from pathlib import Path

from image_quality_auditor.anonymizer import anonymize_filename
from image_quality_auditor.config import AuditorConfig
from image_quality_auditor.metrics import ImageLoadError, compute_metrics, load_grayscale
from image_quality_auditor.models import (
    ImageDimensions,
    ImageMetadata,
    ImageMetrics,
    QualityCategory,
)

_EXTENSION_TO_FORMAT: dict[str, str] = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
    ".bmp": "BMP",
    ".tiff": "TIFF",
    ".tif": "TIFF",
    ".webp": "WEBP",
}


def classify_quality(
    metrics: ImageMetrics | None,
    dimensions: ImageDimensions | None,
    config: AuditorConfig,
) -> QualityCategory:
    """Classify image quality by comparing metrics against config thresholds.

    Rules are evaluated in priority order (first match wins):
        1. CORRUPTED   - metrics/dimensions unavailable (decode failed)
        2. POOR        - hard failures: exposure out of range, too blurry,
                        or below minimum dimensions (disqualifying)
        3. ACCEPTABLE  - soft failure: low contrast (usable but not ideal)
        4. GOOD        - passes all checks

    Args:
        metrics: Computed metrics, or None if the image could not be decoded.
        dimensions: Image dimensions, or None if decode failed.
        config: Configuration providing the classification thresholds.

    Returns:
        The QualityCategory for this image.
    """

    # Corrupted: nothing to evaluate.
    if metrics is None or dimensions is None:
        return QualityCategory.CORRUPTED

    # Hard failures -> POOR (disqualifying for downstream AI training).
    if metrics.mean_brightness < config.min_brightness:
        return QualityCategory.POOR
    if metrics.mean_brightness > config.max_brightness:
        return QualityCategory.POOR
    if metrics.sharpness_laplacian_variance < config.min_sharpness:
        return QualityCategory.POOR
    if not dimensions.meets_minimum(config.min_width, config.min_height):
        return QualityCategory.POOR

    # Soft failure -> ACCEPTABLE (usable, below recommended).
    if metrics.contrast_std < config.min_contrast:
        return QualityCategory.ACCEPTABLE

    # Passed everything.
    return QualityCategory.GOOD


def scan_file(path: Path, config: AuditorConfig) -> ImageMetadata:
    """Audit a single image file into an ImageMetadata record.

    Gathers filesystem facts, anonymizes the filename, attempts to load and
    measure the image, then classifies it. Oversized files are rejected
    before loading (decompression-bomb protection). Any decode failure is
    captured as CORRUPTED with an error message rather than raised.

    Args:
        path: Path to the image file.
        config: Configuration providing thresholds and the size limit.

    Returns:
        A fully populated ImageMetadata record.
    """

    file_size_bytes = path.stat().st_size
    filename_original = path.name
    filename_anonymized = anonymize_filename(filename_original)
    file_format = _EXTENSION_TO_FORMAT.get(path.suffix.lower(), "UNKNOWN")

    dimensions: ImageDimensions | None = None
    metrics: ImageMetrics | None = None
    error: str | None = None

    if file_size_bytes > config.max_file_size_bytes:
        # Do not load oversized files (bomb protection).
        error = (
            f"File size {file_size_bytes} bytes exceeds the configured "
            f"limit of {config.max_file_size_bytes} bytes"
        )

    else:
        try:
            gray = load_grayscale(path)
            height, width = gray.shape[0], gray.shape[1]
            dimensions = ImageDimensions(width=width, height=height)
            metrics = compute_metrics(gray)
        except ImageLoadError as exc:
            error = str(exc)

    quality_category = classify_quality(metrics, dimensions, config)

    return ImageMetadata(
        file_path=path,
        filename_original=filename_original,
        filename_anonymized=filename_anonymized,
        file_size_bytes=file_size_bytes,
        file_format=file_format,
        dimensions=dimensions,
        metrics=metrics,
        quality_category=quality_category,
        error=error,
    )


def scan_folder(folder: Path, config: AuditorConfig) -> list[ImageMetadata]:
    """Scan a folder and audit every supported image file within it.

    Only files whose extension maps to a format listed in
    config.allowed_formats are processed; other files are ignored. Results
    are returned in sorted filename order for deterministic output.

    Args:
        folder: Path to the directory to scan (non-recursive).
        config: Configuration providing thresholds and allowed formats.

    Returns:
        One ImageMetadata record per processed image file.

    Raises:
        NotADirectoryError: If `folder` is not an existing directory.
    """
    if not folder.is_dir():
        msg = f"Not a directory: {folder}"
        raise NotADirectoryError(msg)

    results: list[ImageMetadata] = []
    for path in sorted(folder.iterdir()):
        if not path.is_file():
            continue
        image_format = _EXTENSION_TO_FORMAT.get(path.suffix.lower())
        if image_format is None or image_format not in config.allowed_formats:
            continue
        results.append(scan_file(path, config))

    return results
