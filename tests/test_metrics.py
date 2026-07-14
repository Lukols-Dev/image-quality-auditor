"""Unit tests for image quality metrics.

Tests use synthetic NumPy images with known properties (uniform black,
uniform white, half/half, checkerboard) so expected metric values can be
asserted precisely — no real image files are needed. File-loading tests
use cv2.imwrite to create temporary images on tmp_path.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from image_quality_auditor.metrics import (
    ImageLoadError,
    compute_brightness,
    compute_contrast,
    compute_metrics,
    compute_sharpness,
    load_grayscale,
)
from image_quality_auditor.models import ImageMetrics

# ============================================================
# Synthetic image helpers
# ============================================================


def _uniform(value: int, size: int = 100) -> np.ndarray:
    """A uniform grayscale image where every pixel equals `value`."""
    return np.full((size, size), value, dtype=np.uint8)


def _half_black_white(size: int = 100) -> np.ndarray:
    """Top half white (255), bottom half black (0)."""
    img = np.zeros((size, size), dtype=np.uint8)
    img[: size // 2, :] = 255
    return img


def _checkerboard(size: int = 100) -> np.ndarray:
    """A checkerboard pattern with many edges (high sharpness)."""
    img = np.zeros((size, size), dtype=np.uint8)
    img[::2, ::2] = 255
    img[1::2, 1::2] = 255
    return img


# ============================================================
# Tests
# ============================================================


class TestComputeBrightness:
    """Tests for compute_brightness (mean pixel value)."""

    def test_black_image_is_zero(self) -> None:
        """A fully black image has brightness 0."""
        assert compute_brightness(_uniform(0)) == 0.0

    def test_white_image_is_255(self) -> None:
        """A fully white image has brightness 255."""
        assert compute_brightness(_uniform(255)) == 255.0

    def test_uniform_gray(self) -> None:
        """A uniform gray image has brightness equal to that gray value."""
        assert compute_brightness(_uniform(128)) == 128.0

    def test_half_black_white_is_midpoint(self) -> None:
        """A half-white, half-black image averages to ~127.5."""
        assert compute_brightness(_half_black_white()) == pytest.approx(127.5)

    def test_returns_python_float(self) -> None:
        """The result is a native Python float, not numpy.float64."""
        result = compute_brightness(_uniform(100))
        assert type(result) is float


class TestComputeContrast:
    """Tests for compute_contrast (standard deviation)."""

    def test_uniform_image_zero_contrast(self) -> None:
        """A uniform image has zero contrast (no variation)."""
        assert compute_contrast(_uniform(128)) == 0.0

    def test_black_image_zero_contrast(self) -> None:
        """A fully black image has zero contrast."""
        assert compute_contrast(_uniform(0)) == 0.0

    def test_half_black_white_high_contrast(self) -> None:
        """A half-black, half-white image has maximum contrast (~127.5)."""
        # std of a 50/50 split of 0 and 255 is exactly 127.5
        assert compute_contrast(_half_black_white()) == pytest.approx(127.5)

    def test_returns_python_float(self) -> None:
        """The result is a native Python float."""
        result = compute_contrast(_half_black_white())
        assert type(result) is float


class TestComputeSharpness:
    """Tests for compute_sharpness (variance of the Laplacian)."""

    def test_uniform_image_near_zero(self) -> None:
        """A uniform image has ~zero sharpness (no edges)."""
        assert compute_sharpness(_uniform(128)) == pytest.approx(0.0)

    def test_checkerboard_high_sharpness(self) -> None:
        """A checkerboard has high sharpness (many edges)."""
        assert compute_sharpness(_checkerboard()) > 1000.0

    def test_sharp_greater_than_blurred(self) -> None:
        """A sharp image scores higher than its blurred version."""
        sharp = _checkerboard()
        blurred = cv2.GaussianBlur(sharp, (15, 15), 0)
        assert compute_sharpness(sharp) > compute_sharpness(blurred)

    def test_returns_python_float(self) -> None:
        """The result is a native Python float."""
        result = compute_sharpness(_checkerboard())
        assert type(result) is float

    def test_never_negative(self) -> None:
        """Variance is always non-negative."""
        assert compute_sharpness(_uniform(50)) >= 0.0


class TestComputeMetrics:
    """Tests for compute_metrics (combined ImageMetrics)."""

    def test_returns_image_metrics(self) -> None:
        """compute_metrics returns an ImageMetrics instance."""
        result = compute_metrics(_half_black_white())
        assert isinstance(result, ImageMetrics)

    def test_values_match_individual_functions(self) -> None:
        """Combined metrics match the individual metric functions."""
        img = _half_black_white()
        metrics = compute_metrics(img)
        assert metrics.mean_brightness == compute_brightness(img)
        assert metrics.contrast_std == compute_contrast(img)
        assert metrics.sharpness_laplacian_variance == compute_sharpness(img)

    def test_result_is_frozen(self) -> None:
        """The returned ImageMetrics is immutable."""
        from pydantic import ValidationError

        metrics = compute_metrics(_uniform(128))
        with pytest.raises(ValidationError):
            metrics.mean_brightness = 200.0  # type: ignore[misc]

    def test_black_image_metrics(self) -> None:
        """A black image yields brightness 0, contrast 0, sharpness ~0."""
        metrics = compute_metrics(_uniform(0))
        assert metrics.mean_brightness == 0.0
        assert metrics.contrast_std == 0.0
        assert metrics.sharpness_laplacian_variance == pytest.approx(0.0)


class TestLoadGrayscale:
    """Tests for load_grayscale (file loading and conversion)."""

    def test_loads_color_image_as_grayscale(self, tmp_path: Path) -> None:
        """A color image is loaded and converted to a 2D grayscale array."""
        # Create a color (3-channel) image on disk.
        color = np.full((50, 50, 3), (255, 128, 0), dtype=np.uint8)
        image_path = tmp_path / "color.png"
        cv2.imwrite(str(image_path), color)

        gray = load_grayscale(image_path)

        assert gray.ndim == 2  # grayscale is 2D (no color channel)
        assert gray.shape == (50, 50)
        assert gray.dtype == np.uint8

    def test_loads_existing_png(self, tmp_path: Path) -> None:
        """A written PNG can be loaded back."""
        img = _uniform(200)
        image_path = tmp_path / "gray.png"
        cv2.imwrite(str(image_path), img)

        loaded = load_grayscale(image_path)

        assert loaded.shape == (100, 100)

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        """Loading a nonexistent file raises ImageLoadError."""
        missing = tmp_path / "does_not_exist.png"
        with pytest.raises(ImageLoadError):
            load_grayscale(missing)

    def test_non_image_file_raises(self, tmp_path: Path) -> None:
        """Loading a file that is not an image raises ImageLoadError."""
        fake = tmp_path / "fake.png"
        fake.write_text("this is not an image")
        with pytest.raises(ImageLoadError):
            load_grayscale(fake)

    def test_round_trip_brightness(self, tmp_path: Path) -> None:
        """A uniform image written and reloaded keeps its brightness."""
        img = _uniform(100)
        image_path = tmp_path / "uniform.png"
        cv2.imwrite(str(image_path), img)

        loaded = load_grayscale(image_path)

        assert compute_brightness(loaded) == pytest.approx(100.0)
