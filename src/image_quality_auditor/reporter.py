"""Report generation from audit results.

Turns the per-image records produced by the scanner into aggregate
statistics and output artifacts (CSV for data analysis, HTML for humans).

compute_summary is pure computation; the write_* functions handle I/O.
"""

from __future__ import annotations

from collections import Counter
from csv import DictWriter
from pathlib import Path
from statistics import mean

from jinja2 import Environment, PackageLoader

from image_quality_auditor.models import (
    AuditResult,
    AuditSummary,
    CategoryCounts,
    ImageMetadata,
    QualityCategory,
)


def compute_summary(
    images: list[ImageMetadata],
    duration_seconds: float,
) -> AuditSummary:
    """Aggregate per-image records into run-level statistics.

    Averaged metrics are computed only over images that were successfully
    decoded (those with metrics present). When every image is corrupted —
    or the list is empty — the averages are None.

    Args:
        images: Per-image audit records from the scanner.
        duration_seconds: Wall-clock duration of the audit run.

    Returns:
        An AuditSummary with category counts and averaged metrics.
    """
    valid_metrics = [img.metrics for img in images if img.metrics is not None]

    mean_brightness_avg: float | None = None
    contrast_std_avg: float | None = None
    sharpness_avg: float | None = None

    if valid_metrics:
        mean_brightness_avg = mean(m.mean_brightness for m in valid_metrics)
        contrast_std_avg = mean(m.contrast_std for m in valid_metrics)
        sharpness_avg = mean(m.sharpness_laplacian_variance for m in valid_metrics)

    by_category = Counter[QualityCategory](img.quality_category for img in images)

    counts = CategoryCounts(
        good=by_category[QualityCategory.GOOD],
        acceptable=by_category[QualityCategory.ACCEPTABLE],
        poor=by_category[QualityCategory.POOR],
        corrupted=by_category[QualityCategory.CORRUPTED],
    )

    return AuditSummary(
        total_files_scanned=len(images),
        counts=counts,
        duration_seconds=duration_seconds,
        mean_brightness_avg=mean_brightness_avg,
        contrast_std_avg=contrast_std_avg,
        sharpness_avg=sharpness_avg,
    )


_COLUMNS: tuple[str, ...] = (
    "filename_anonymized",
    "quality_category",
    "file_format",
    "file_size_bytes",
    "width",
    "height",
    "mean_brightness",
    "contrast_std",
    "sharpness_laplacian_variance",
    "error",
)


def _to_row(image: ImageMetadata) -> dict[str, object]:
    """Flatten one audit record into a CSV row.

    All columns are present in every row (DictWriter requires it); values
    unavailable for corrupted images stay None and become empty cells.
    """
    row: dict[str, object] = {
        "filename_anonymized": image.filename_anonymized,
        "quality_category": image.quality_category.value,
        "file_format": image.file_format,
        "file_size_bytes": image.file_size_bytes,
        "width": None,
        "height": None,
        "mean_brightness": None,
        "contrast_std": None,
        "sharpness_laplacian_variance": None,
        "error": image.error,
    }

    if image.dimensions is not None:
        row["width"] = image.dimensions.width
        row["height"] = image.dimensions.height

    if image.metrics is not None:
        row["mean_brightness"] = image.metrics.mean_brightness
        row["contrast_std"] = image.metrics.contrast_std
        row["sharpness_laplacian_variance"] = image.metrics.sharpness_laplacian_variance

    return row


def write_csv(
    images: list[ImageMetadata],
    output_path: Path,
) -> None:
    """Write per-image audit records to a CSV file.

    One row per image. Nested dimensions and metrics are flattened into
    separate columns; missing values (corrupted images) are written as
    empty cells.

    Args:
        images: Per-image audit records from the scanner.
        output_path: Destination file path. Parent directories are created
            if they do not exist.
    """

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = DictWriter(handle, fieldnames=_COLUMNS)
        writer.writeheader()
        writer.writerows(_to_row(image) for image in images)


def write_json(result: AuditResult, output_path: Path) -> None:
    """Write the complete audit result (images + summary) as JSON.

    Args:
        result: The audit result to serialize.
        output_path: Destination file path. Parent directories are created
            if they do not exist.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")


def write_html(result: AuditResult, output_path: Path) -> None:
    """Render the audit result as a standalone HTML report.

    The template is loaded from the package's templates/ directory and the
    output is a single self-contained file (CSS inlined, no external
    assets), so it can be opened or emailed as-is.

    Args:
        result: The audit result to render.
        output_path: Destination file path. Parent directories are created
            if they do not exist.
    """
    # autoescape=True unconditionally: the report embeds untrusted text
    # (e.g. decode-error messages), and the template's ".html.jinja2" name
    # would slip past select_autoescape(["html"]), leaving escaping off.
    env = Environment(
        loader=PackageLoader("image_quality_auditor", "templates"),
        autoescape=True,
    )
    template = env.get_template("report.html.jinja2")
    html = template.render(images=result.images, summary=result.summary)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
