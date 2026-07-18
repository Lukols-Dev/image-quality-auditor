"""Unit tests for folder scanning and quality classification.

classify_quality is tested directly with constructed metrics/dimensions.
scan_file and scan_folder are tested against synthetic images written to
pytest's tmp_path, covering good/poor/corrupted images, format filtering,
and oversized-file rejection.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from image_quality_auditor.config import AuditorConfig
from image_quality_auditor.models import (
    ImageDimensions,
    ImageMetrics,
    QualityCategory,
)
from image_quality_auditor.scanner import (
    classify_quality,
    scan_file,
    scan_folder,
)


@pytest.fixture
def config() -> AuditorConfig:
    """A default configuration isolated from any local .env file."""
    return AuditorConfig(_env_file=None)


# ============================================================
# Image-writing helpers
# ============================================================


def _write_image(path: Path, array: np.ndarray) -> None:
    """Write a NumPy array to disk as an image via OpenCV."""
    cv2.imwrite(str(path), array)


def _good_image() -> np.ndarray:
    """A bright, sharp, sufficiently large color image."""
    # Random noise gives high contrast and high sharpness.
    rng = np.random.default_rng(seed=42)
    return rng.integers(50, 200, (1000, 1000, 3), dtype=np.uint8)


def _black_image(size: int = 1000) -> np.ndarray:
    """A fully black (underexposed) image."""
    return np.zeros((size, size, 3), dtype=np.uint8)


# ============================================================
# classify_quality
# ============================================================


class TestClassifyQuality:
    """Tests for the threshold-driven classification logic."""

    def _metrics(
        self,
        brightness: float = 128.0,
        contrast: float = 50.0,
        sharpness: float = 500.0,
    ) -> ImageMetrics:
        return ImageMetrics(
            mean_brightness=brightness,
            contrast_std=contrast,
            sharpness_laplacian_variance=sharpness,
        )

    def _dims(self, width: int = 1920, height: int = 1080) -> ImageDimensions:
        return ImageDimensions(width=width, height=height)

    def test_good_image(self, config: AuditorConfig) -> None:
        """An image passing all checks is GOOD."""
        result = classify_quality(self._metrics(), self._dims(), config)
        assert result is QualityCategory.GOOD

    def test_none_metrics_is_corrupted(self, config: AuditorConfig) -> None:
        """Missing metrics classify as CORRUPTED."""
        result = classify_quality(None, None, config)
        assert result is QualityCategory.CORRUPTED

    def test_none_dimensions_is_corrupted(self, config: AuditorConfig) -> None:
        """Missing dimensions classify as CORRUPTED."""
        result = classify_quality(self._metrics(), None, config)
        assert result is QualityCategory.CORRUPTED

    def test_too_dark_is_poor(self, config: AuditorConfig) -> None:
        """Brightness below min_brightness is POOR."""
        result = classify_quality(self._metrics(brightness=10.0), self._dims(), config)
        assert result is QualityCategory.POOR

    def test_too_bright_is_poor(self, config: AuditorConfig) -> None:
        """Brightness above max_brightness is POOR."""
        result = classify_quality(self._metrics(brightness=240.0), self._dims(), config)
        assert result is QualityCategory.POOR

    def test_too_blurry_is_poor(self, config: AuditorConfig) -> None:
        """Sharpness below min_sharpness is POOR."""
        result = classify_quality(self._metrics(sharpness=30.0), self._dims(), config)
        assert result is QualityCategory.POOR

    def test_too_small_is_poor(self, config: AuditorConfig) -> None:
        """Dimensions below the minimum are POOR."""
        result = classify_quality(self._metrics(), self._dims(width=320, height=240), config)
        assert result is QualityCategory.POOR

    def test_low_contrast_is_acceptable(self, config: AuditorConfig) -> None:
        """Low contrast (but otherwise fine) is ACCEPTABLE."""
        result = classify_quality(self._metrics(contrast=10.0), self._dims(), config)
        assert result is QualityCategory.ACCEPTABLE

    def test_hard_failure_takes_priority_over_soft(self, config: AuditorConfig) -> None:
        """A hard failure (dark) outranks a soft one (low contrast)."""
        # Both too dark AND low contrast -> POOR wins (checked first).
        result = classify_quality(
            self._metrics(brightness=10.0, contrast=5.0),
            self._dims(),
            config,
        )
        assert result is QualityCategory.POOR


# ============================================================
# scan_file
# ============================================================


class TestScanFile:
    """Tests for auditing a single file."""

    def test_good_image_metadata(self, tmp_path: Path, config: AuditorConfig) -> None:
        """A good image produces a complete, non-corrupted record."""
        path = tmp_path / "good.png"
        _write_image(path, _good_image())

        meta = scan_file(path, config)

        assert meta.filename_original == "good.png"
        assert meta.file_format == "PNG"
        assert meta.dimensions is not None
        assert meta.metrics is not None
        assert not meta.is_corrupted

    def test_filename_is_anonymized(self, tmp_path: Path, config: AuditorConfig) -> None:
        """The anonymized filename differs from the original stem."""
        path = tmp_path / "patient_001.png"
        _write_image(path, _good_image())

        meta = scan_file(path, config)

        assert "patient_001" not in meta.filename_anonymized
        assert meta.filename_anonymized.endswith(".png")

    def test_black_image_is_poor(self, tmp_path: Path, config: AuditorConfig) -> None:
        """A black image is classified POOR (underexposed)."""
        path = tmp_path / "dark.png"
        _write_image(path, _black_image())

        meta = scan_file(path, config)

        assert meta.quality_category is QualityCategory.POOR

    def test_corrupted_file(self, tmp_path: Path, config: AuditorConfig) -> None:
        """A non-image file is recorded as CORRUPTED with an error."""
        path = tmp_path / "broken.png"
        path.write_text("this is not an image")

        meta = scan_file(path, config)

        assert meta.is_corrupted
        assert meta.metrics is None
        assert meta.error is not None

    def test_dimensions_orientation(self, tmp_path: Path, config: AuditorConfig) -> None:
        """Width and height are recorded in the correct order."""
        # Non-square image: 800 wide x 600 tall.
        array = np.random.default_rng(1).integers(50, 200, (600, 800, 3), dtype=np.uint8)
        path = tmp_path / "landscape.png"
        _write_image(path, array)

        meta = scan_file(path, config)

        assert meta.dimensions is not None
        assert meta.dimensions.width == 800
        assert meta.dimensions.height == 600

    def test_oversized_file_rejected(self, tmp_path: Path) -> None:
        """A file above the size limit is rejected before loading."""
        # Config with a tiny max size so any real image exceeds it.
        tiny_config = AuditorConfig(_env_file=None, max_file_size_mb=0.0001)
        path = tmp_path / "big.png"
        _write_image(path, _good_image())

        meta = scan_file(path, tiny_config)

        assert meta.is_corrupted
        assert meta.error is not None
        assert "exceeds" in meta.error


# ============================================================
# scan_folder
# ============================================================


class TestScanFolder:
    """Tests for scanning a directory."""

    def test_empty_folder(self, tmp_path: Path, config: AuditorConfig) -> None:
        """An empty folder yields no results."""
        assert scan_folder(tmp_path, config) == []

    def test_processes_multiple_images(self, tmp_path: Path, config: AuditorConfig) -> None:
        """All supported images in the folder are processed."""
        _write_image(tmp_path / "a.png", _good_image())
        _write_image(tmp_path / "b.png", _good_image())
        _write_image(tmp_path / "c.png", _black_image())

        results = scan_folder(tmp_path, config)

        assert len(results) == 3

    def test_ignores_non_image_files(self, tmp_path: Path, config: AuditorConfig) -> None:
        """Files without a supported image extension are ignored."""
        _write_image(tmp_path / "image.png", _good_image())
        (tmp_path / "notes.txt").write_text("not an image")
        (tmp_path / "data.json").write_text("{}")

        results = scan_folder(tmp_path, config)

        assert len(results) == 1
        assert results[0].filename_original == "image.png"

    def test_results_sorted_by_name(self, tmp_path: Path, config: AuditorConfig) -> None:
        """Results are returned in sorted filename order."""
        _write_image(tmp_path / "c.png", _good_image())
        _write_image(tmp_path / "a.png", _good_image())
        _write_image(tmp_path / "b.png", _good_image())

        results = scan_folder(tmp_path, config)

        names = [r.filename_original for r in results]
        assert names == ["a.png", "b.png", "c.png"]

    def test_mixed_folder_resilience(self, tmp_path: Path, config: AuditorConfig) -> None:
        """A corrupted file does not stop processing of valid files."""
        _write_image(tmp_path / "good.png", _good_image())
        (tmp_path / "broken.png").write_text("corrupted")
        _write_image(tmp_path / "dark.png", _black_image())

        results = scan_folder(tmp_path, config)

        assert len(results) == 3
        categories = {r.filename_original: r.quality_category for r in results}
        assert categories["broken.png"] is QualityCategory.CORRUPTED

    def test_not_a_directory_raises(self, tmp_path: Path, config: AuditorConfig) -> None:
        """Scanning a non-directory path raises NotADirectoryError."""
        file_path = tmp_path / "file.png"
        _write_image(file_path, _good_image())

        with pytest.raises(NotADirectoryError):
            scan_folder(file_path, config)
