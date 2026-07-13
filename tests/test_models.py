"""Unit test for domains models.

Tests verify our design decisions (constraints, immutability, computed
properties) — not Pydantic's core validation engine. Each model has a
dedicated test class following the Arrange-Act-Assert pattern.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from image_quality_auditor.models import (
    AuditResult,
    AuditSummary,
    CategoryCounts,
    ImageDimensions,
    ImageMetadata,
    ImageMetrics,
    QualityCategory,
)


class TestQualityCategory:
    """Tests for the QualityCategory enum."""

    def test_has_four_categories(self) -> None:
        """Enum defines exactly four quality levels."""
        assert len(QualityCategory) == 4

    def test_values_are_lower_case_strings(self) -> None:
        """Enum values are lowercase strings."""
        for category in QualityCategory:
            assert category.value == category.value.lower()

    def test_string_equality(self) -> None:
        """StrEnum members compare equal to their string values."""
        assert QualityCategory.GOOD == "good"  # type: ignore[comparison-overlap]
        assert QualityCategory.CORRUPTED == "corrupted"  # type: ignore[comparison-overlap]

    def test_construction_from_string(self) -> None:
        """A category can be constructed from its string value."""
        assert QualityCategory("good") is QualityCategory.GOOD
        assert QualityCategory("poor") is QualityCategory.POOR

    def test_unknown_value_raises_error(self) -> None:
        """An unknown value raises a ValueError."""
        with pytest.raises(ValueError):
            QualityCategory("unknown")

    def test_is_iterable(self) -> None:
        """All categories can be iterated (useful for reports)."""
        categories = list[QualityCategory](QualityCategory)
        assert QualityCategory.GOOD in categories
        assert len(categories) == 4


class TestImageDimensions:
    """Tests for the ImageDimensions value object."""

    def test_creation_with_valid_values(self) -> None:
        """Dimensions are created from positive width and height."""
        dims = ImageDimensions(width=100, height=200)
        assert dims.width == 100
        assert dims.height == 200

    def test_zero_width_rejected(self) -> None:
        """Zero width raises a ValidationError."""
        with pytest.raises(ValidationError):
            ImageDimensions(width=0, height=200)

    def test_zero_height_rejected(self) -> None:
        """Height must be strictly positive (gt=0)."""
        with pytest.raises(ValidationError):
            ImageDimensions(width=640, height=0)

    def test_negative_dimensions_rejected(self) -> None:
        """Negative dimensions are invalid."""
        with pytest.raises(ValidationError):
            ImageDimensions(width=-10, height=480)

    def test_total_pixels(self) -> None:
        """total_pixels returns width times height."""
        dims = ImageDimensions(width=640, height=480)
        assert dims.total_pixels == 307_200

    def test_aspect_ratio(self) -> None:
        """aspect_ratio returns width divided by height."""
        dims = ImageDimensions(width=1920, height=1080)
        assert dims.aspect_ratio == pytest.approx(1.777, abs=0.001)

    def test_meets_minimum_when_larger(self) -> None:
        """meets_minimum is True when both dimensions exceed the minimum."""
        dims = ImageDimensions(width=1920, height=1080)
        assert dims.meets_minimum(640, 480) is True

    def test_meets_minimum_when_equal(self) -> None:
        """meets_minimum is True when dimensions equal the minimum."""
        dims = ImageDimensions(width=640, height=480)
        assert dims.meets_minimum(640, 480) is True

    def test_meets_minimum_when_smaller(self) -> None:
        """meets_minimum is False when a dimension is below the minimum."""
        dims = ImageDimensions(width=320, height=240)
        assert dims.meets_minimum(640, 480) is False

    def test_meets_minimum_partial_fail(self) -> None:
        """meets_minimum is False when only one dimension is too small."""
        dims = ImageDimensions(width=1920, height=200)
        assert dims.meets_minimum(640, 480) is False

    def test_is_frozen(self) -> None:
        """Dimensions are immutable after creation."""
        dims = ImageDimensions(width=640, height=480)
        with pytest.raises(ValidationError):
            dims.width = 1024

    def test_equality(self) -> None:
        """Value objects with the same values are equal."""
        a = ImageDimensions(width=640, height=480)
        b = ImageDimensions(width=640, height=480)
        assert a == b

    def test_inequality(self) -> None:
        """Value objects with different values are not equal."""
        a = ImageDimensions(width=640, height=480)
        b = ImageDimensions(width=800, height=600)
        assert a != b

    def test_hashable(self) -> None:
        """Frozen models are hashable and usable in sets."""
        a = ImageDimensions(width=640, height=480)
        b = ImageDimensions(width=640, height=480)
        c = ImageDimensions(width=800, height=600)
        assert len({a, b, c}) == 2


class TestImageMetrics:
    """Tests for the ImageMetrics value object."""

    def test_creation_with_valid_values(self) -> None:
        """Metrics are created from valid brightness, contrast, sharpness."""
        metrics = ImageMetrics(
            mean_brightness=128.5,
            contrast_std=45.0,
            sharpness_laplacian_variance=500.0,
        )
        assert metrics.mean_brightness == 128.5
        assert metrics.contrast_std == 45.0
        assert metrics.sharpness_laplacian_variance == 500.0

    def test_brightness_lower_bound(self) -> None:
        """Brightness of exactly 0.0 (pure black) is valid."""
        metrics = ImageMetrics(
            mean_brightness=0.0,
            contrast_std=0.0,
            sharpness_laplacian_variance=0.0,
        )
        assert metrics.mean_brightness == 0.0

    def test_brightness_upper_bound(self) -> None:
        """Brightness of exactly 255.0 (pure white) is valid."""
        metrics = ImageMetrics(
            mean_brightness=255.0,
            contrast_std=0.0,
            sharpness_laplacian_variance=0.0,
        )
        assert metrics.mean_brightness == 255.0

    def test_brightness_above_range_rejected(self) -> None:
        """Brightness above 255 is invalid for uint8 images."""
        with pytest.raises(ValidationError):
            ImageMetrics(
                mean_brightness=300.0,
                contrast_std=45.0,
                sharpness_laplacian_variance=500.0,
            )

    def test_brightness_below_range_rejected(self) -> None:
        """Negative brightness is invalid."""
        with pytest.raises(ValidationError):
            ImageMetrics(
                mean_brightness=-10.0,
                contrast_std=45.0,
                sharpness_laplacian_variance=500.0,
            )

    def test_negative_contrast_rejected(self) -> None:
        """Contrast (standard deviation) cannot be negative."""
        with pytest.raises(ValidationError):
            ImageMetrics(
                mean_brightness=128.0,
                contrast_std=-5.0,
                sharpness_laplacian_variance=500.0,
            )

    def test_negative_sharpness_rejected(self) -> None:
        """Sharpness (variance) cannot be negative."""
        with pytest.raises(ValidationError):
            ImageMetrics(
                mean_brightness=128.0,
                contrast_std=45.0,
                sharpness_laplacian_variance=-100.0,
            )

    def test_is_frozen(self) -> None:
        """Metrics are immutable after creation."""
        metrics = ImageMetrics(
            mean_brightness=128.0,
            contrast_std=45.0,
            sharpness_laplacian_variance=500.0,
        )
        with pytest.raises(ValidationError):
            metrics.mean_brightness = 200.0

    def test_equality(self) -> None:
        """Metrics with identical values are equal."""
        a = ImageMetrics(
            mean_brightness=128.0,
            contrast_std=45.0,
            sharpness_laplacian_variance=500.0,
        )
        b = ImageMetrics(
            mean_brightness=128.0,
            contrast_std=45.0,
            sharpness_laplacian_variance=500.0,
        )
        assert a == b

    def test_type_coercion_from_int(self) -> None:
        """Integer inputs are coerced to float (lax mode)."""
        metrics = ImageMetrics(
            mean_brightness=128,
            contrast_std=45,
            sharpness_laplacian_variance=500,
        )
        assert isinstance(metrics.mean_brightness, float)
        assert metrics.mean_brightness == 128.0


class TestImageMetadata:
    """Tests for the ImageMetadata entity."""

    def _good_metadata(self) -> ImageMetadata:
        """Helper: build a valid, non-corrupted ImageMetadata."""
        return ImageMetadata(
            file_path=Path("/photos/patient_001.jpg"),
            filename_original="patient_001.jpg",
            filename_anonymized="a3f2c1d4.jpg",
            file_size_bytes=204_800,
            file_format="JPEG",
            dimensions=ImageDimensions(width=1920, height=1080),
            metrics=ImageMetrics(
                mean_brightness=128.0,
                contrast_std=45.0,
                sharpness_laplacian_variance=500.0,
            ),
            quality_category=QualityCategory.GOOD,
        )

    def test_creation_full_record(self) -> None:
        """A complete metadata record is created for a good image."""
        meta = self._good_metadata()
        assert meta.filename_original == "patient_001.jpg"
        assert meta.quality_category is QualityCategory.GOOD
        assert meta.dimensions is not None
        assert meta.metrics is not None

    def test_corrupted_record_has_no_metrics(self) -> None:
        """A corrupted image has None dimensions and metrics."""
        meta = ImageMetadata(
            file_path=Path("/photos/broken.jpg"),
            filename_original="broken.jpg",
            filename_anonymized="ff00ee11.jpg",
            file_size_bytes=0,
            file_format="UNKNOWN",
            quality_category=QualityCategory.CORRUPTED,
            error="Cannot decode: truncated JPEG",
        )
        assert meta.dimensions is None
        assert meta.metrics is None
        assert meta.error == "Cannot decode: truncated JPEG"

    def test_is_corrupted_true(self) -> None:
        """is_corrupted is True for CORRUPTED category."""
        meta = ImageMetadata(
            file_path=Path("/photos/broken.jpg"),
            filename_original="broken.jpg",
            filename_anonymized="ff.jpg",
            file_size_bytes=0,
            file_format="UNKNOWN",
            quality_category=QualityCategory.CORRUPTED,
        )
        assert meta.is_corrupted is True

    def test_is_corrupted_false(self) -> None:
        """is_corrupted is False for non-CORRUPTED categories."""
        meta = self._good_metadata()
        assert meta.is_corrupted is False

    def test_path_coercion_from_string(self) -> None:
        """A string file_path is coerced to a Path object."""
        meta = ImageMetadata(
            file_path="/photos/test.png",  # type: ignore[arg-type]
            filename_original="test.png",
            filename_anonymized="aa.png",
            file_size_bytes=100,
            file_format="PNG",
            quality_category=QualityCategory.GOOD,
        )
        assert isinstance(meta.file_path, Path)
        assert meta.file_path.suffix == ".png"

    def test_file_size_kb(self) -> None:
        """file_size_kb converts bytes to kilobytes (binary)."""
        meta = ImageMetadata(
            file_path=Path("/a.jpg"),
            filename_original="a.jpg",
            filename_anonymized="x.jpg",
            file_size_bytes=2048,  # 2 KB
            file_format="JPEG",
            quality_category=QualityCategory.GOOD,
        )
        assert meta.file_size_kb == 2.0

    def test_file_size_mb(self) -> None:
        """file_size_mb converts bytes to megabytes (binary)."""
        meta = ImageMetadata(
            file_path=Path("/a.jpg"),
            filename_original="a.jpg",
            filename_anonymized="x.jpg",
            file_size_bytes=2_097_152,  # 2 MB
            file_format="JPEG",
            quality_category=QualityCategory.GOOD,
        )
        assert meta.file_size_mb == pytest.approx(2.0)

    def test_empty_original_filename_rejected(self) -> None:
        """An empty original filename is invalid (min_length=1)."""
        with pytest.raises(ValidationError):
            ImageMetadata(
                file_path=Path("/a.jpg"),
                filename_original="",
                filename_anonymized="x.jpg",
                file_size_bytes=100,
                file_format="JPEG",
                quality_category=QualityCategory.GOOD,
            )

    def test_negative_file_size_rejected(self) -> None:
        """A negative file size is invalid."""
        with pytest.raises(ValidationError):
            ImageMetadata(
                file_path=Path("/a.jpg"),
                filename_original="a.jpg",
                filename_anonymized="x.jpg",
                file_size_bytes=-100,
                file_format="JPEG",
                quality_category=QualityCategory.GOOD,
            )

    def test_missing_required_field_rejected(self) -> None:
        """Omitting a required field raises ValidationError."""
        with pytest.raises(ValidationError):
            ImageMetadata(  # type: ignore[call-arg]
                file_path=Path("/a.jpg"),
                filename_anonymized="x.jpg",
                file_size_bytes=100,
                file_format="JPEG",
                quality_category=QualityCategory.GOOD,
            )

    def test_is_frozen(self) -> None:
        """Metadata is immutable after creation."""
        meta = self._good_metadata()
        with pytest.raises(ValidationError):
            meta.quality_category = QualityCategory.POOR


class TestCategoryCounts:
    """Tests for the CategoryCounts value object."""

    def test_defaults_to_zero(self) -> None:
        """All counters default to zero."""
        counts = CategoryCounts()
        assert counts.good == 0
        assert counts.acceptable == 0
        assert counts.poor == 0
        assert counts.corrupted == 0

    def test_creation_with_values(self) -> None:
        """Counters are set from provided values."""
        counts = CategoryCounts(good=60, acceptable=20, poor=15, corrupted=5)
        assert counts.good == 60
        assert counts.corrupted == 5

    def test_total(self) -> None:
        """total sums all category counts."""
        counts = CategoryCounts(good=60, acceptable=20, poor=15, corrupted=5)
        assert counts.total == 100

    def test_total_of_empty(self) -> None:
        """total of a default (empty) counter is zero."""
        assert CategoryCounts().total == 0

    def test_usable(self) -> None:
        """usable sums GOOD and ACCEPTABLE only."""
        counts = CategoryCounts(good=60, acceptable=20, poor=15, corrupted=5)
        assert counts.usable == 80

    def test_negative_count_rejected(self) -> None:
        """Counters cannot be negative."""
        with pytest.raises(ValidationError):
            CategoryCounts(good=-5)

    def test_is_frozen(self) -> None:
        """Counts are immutable after creation."""
        counts = CategoryCounts(good=10)
        with pytest.raises(ValidationError):
            counts.good = 20


class TestAuditSummary:
    """Tests for the AuditSummary model."""

    def test_creation_full(self) -> None:
        """A full summary is created with all fields."""
        summary = AuditSummary(
            total_files_scanned=100,
            counts=CategoryCounts(good=60, acceptable=20, poor=15, corrupted=5),
            duration_seconds=12.5,
            mean_brightness_avg=128.3,
            contrast_std_avg=42.7,
            sharpness_avg=520.0,
        )
        assert summary.total_files_scanned == 100
        assert summary.counts.total == 100
        assert summary.mean_brightness_avg == 128.3

    def test_averages_default_to_none(self) -> None:
        """Averaged metrics are None when omitted (all corrupted case)."""
        summary = AuditSummary(
            total_files_scanned=5,
            counts=CategoryCounts(corrupted=5),
            duration_seconds=2.1,
        )
        assert summary.mean_brightness_avg is None
        assert summary.contrast_std_avg is None
        assert summary.sharpness_avg is None

    def test_counts_from_dict(self) -> None:
        """Nested counts can be provided as a dict (Pydantic coercion)."""
        summary = AuditSummary(
            total_files_scanned=10,
            counts={"good": 8, "poor": 2},  # type: ignore[arg-type]
            duration_seconds=1.0,
        )
        assert summary.counts.good == 8
        assert summary.counts.total == 10

    def test_negative_duration_rejected(self) -> None:
        """Duration cannot be negative."""
        with pytest.raises(ValidationError):
            AuditSummary(
                total_files_scanned=1,
                counts=CategoryCounts(),
                duration_seconds=-1.0,
            )

    def test_brightness_avg_out_of_range_rejected(self) -> None:
        """Averaged brightness must respect the 0-255 range."""
        with pytest.raises(ValidationError):
            AuditSummary(
                total_files_scanned=1,
                counts=CategoryCounts(good=1),
                duration_seconds=1.0,
                mean_brightness_avg=300.0,
            )

    def test_is_frozen(self) -> None:
        """Summary is immutable after creation."""
        summary = AuditSummary(
            total_files_scanned=1,
            counts=CategoryCounts(good=1),
            duration_seconds=1.0,
        )
        with pytest.raises(ValidationError):
            summary.duration_seconds = 5.0


class TestAuditResult:
    """Tests for the AuditResult top-level model."""

    def _sample_image(self, category: QualityCategory) -> ImageMetadata:
        """Helper: build a minimal ImageMetadata with a given category."""
        return ImageMetadata(
            file_path=Path(f"/photos/{category.value}.jpg"),
            filename_original=f"{category.value}.jpg",
            filename_anonymized="hash.jpg",
            file_size_bytes=1000,
            file_format="JPEG",
            quality_category=category,
        )

    def _sample_summary(self) -> AuditSummary:
        """Helper: build a minimal AuditSummary."""
        return AuditSummary(
            total_files_scanned=2,
            counts=CategoryCounts(good=1, corrupted=1),
            duration_seconds=0.5,
        )

    def test_creation_from_list(self) -> None:
        """images provided as a list are accepted."""
        result = AuditResult(
            images=[  # type: ignore[arg-type]
                self._sample_image(QualityCategory.GOOD),
                self._sample_image(QualityCategory.CORRUPTED),
            ],
            summary=self._sample_summary(),
        )
        assert len(result.images) == 2

    def test_images_coerced_to_tuple(self) -> None:
        """A list of images is coerced to a tuple for immutability."""
        result = AuditResult(
            images=[self._sample_image(QualityCategory.GOOD)],  # type: ignore[arg-type]
            summary=self._sample_summary(),
        )
        assert isinstance(result.images, tuple)

    def test_images_are_read_only(self) -> None:
        """The images tuple does not support item assignment."""
        result = AuditResult(
            images=[self._sample_image(QualityCategory.GOOD)],  # type: ignore[arg-type]
            summary=self._sample_summary(),
        )
        with pytest.raises(TypeError):
            result.images[0] = self._sample_image(QualityCategory.POOR)  # type: ignore[index]

    def test_is_frozen(self) -> None:
        """Result is immutable after creation."""
        result = AuditResult(
            images=[self._sample_image(QualityCategory.GOOD)],  # type: ignore[arg-type]
            summary=self._sample_summary(),
        )
        with pytest.raises(ValidationError):
            result.summary = self._sample_summary()

    def test_serialization_round_trip(self) -> None:
        """A result can be serialized to JSON and validated back."""
        original = AuditResult(
            images=[self._sample_image(QualityCategory.GOOD)],  # type: ignore[arg-type]
            summary=self._sample_summary(),
        )
        json_str = original.model_dump_json()
        restored = AuditResult.model_validate_json(json_str)
        assert restored == original
