"""Domain models for the image quality auditor.

This module defines the data structures that flow through the auditing
pipeline. Models are frozen (immutable) to prevent accidental mutation
between pipeline stages, and use Pydantic v2 for runtime validation
plus IDE type-checking.

The module is organized from atomic to aggregate:
    - QualityCategory:  enum classification
    - ImageDimensions:  pixel width/height (value object)
    - ImageMetrics:     brightness/contrast/sharpness (value object)
    - ImageMetadata:    per-image record (entity)
    - CategoryCounts:   per-category counters
    - AuditSummary:     aggregate statistics
    - AuditResult:      top-level output (images + summary)

Design principles:
    - Single responsibility per model
    - Immutability via ConfigDict(frozen=True)
    - Domain-meaningful constraints via Field(ge=..., le=...)
    - Path objects over strings for filesystem references
    - StrEnum for serialization-friendly enumerations
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

# ============================================================
# Enums
# ============================================================


class QualityCategory(StrEnum):
    """Image quality classification.

    Categories are ordered conceptually from best to worst quality.
    String values are JSON-serializable and human-readable in reports.

    Attributes:
        GOOD:        Passes all configured quality thresholds.
        ACCEPTABLE:  Passes minimum thresholds but below recommended.
        POOR:        Fails one or more quality thresholds.
        CORRUPTED:   File could not be decoded; metrics unavailable.
    """

    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    CORRUPTED = "corrupted"


# ============================================================
# Value objects (small immutable data carriers)
# ============================================================


class ImageDimensions(BaseModel):
    """Physical pixel dimensions of an image.

    A value object - equality is based on width and height values.
    Immutable; once created, dimensions cannot change.
    """

    model_config = ConfigDict(frozen=True)

    width: int = Field(gt=0, description="Image width in pixels")
    height: int = Field(gt=0, description="Image height in pixels")

    @property
    def total_pixels(self) -> int:
        """Total pxels count (width x height)."""
        return self.width * self.height

    @property
    def aspect_ratio(self) -> float:
        """Width-to-height ratio (e.g., 1.78 for 16:9)."""
        return self.width / self.height

    def meets_minimum(self, min_width: int, min_height: int) -> bool:
        """Check whether dimensions meet the given minimum requirements.

        Args:
            min_width: Minimum required width in pixels.
            min_height: Minimum required height in pixels.

        Returns:
            True if both width >= min_width and height >= min_height.
        """
        return self.width >= min_width and self.height >= min_height


class ImageMetrics(BaseModel):
    """Quality metrics computed from image pixel data.

    All metrics are derived from the grayscale representation of the image.
    This is a value object — equality is based on the metric values.

    Mathematical definitions:
        mean_brightness:
            Arithmetic mean of pixel values across the image.
            Range: 0.0-255.0 for standard uint8 images.
            Low values indicate underexposure, high values overexposure.

        contrast_std:
            Standard deviation of pixel values (sqrt of variance).
            Higher values indicate higher contrast.
            Values < 20 suggest a near-monotone image.

        sharpness_laplacian_variance:
            Variance of the Laplacian of the image (cv2.Laplacian then .var()).
            A standard blur-detection metric: higher means sharper.
            Values < 100 typically indicate significant blur.
    """

    model_config = ConfigDict(frozen=True)

    mean_brightness: float = Field(
        ge=0.0,
        le=255.0,
        description="Mean pixel value across the image (0-255 for uint8)",
    )
    contrast_std: float = Field(
        ge=0.0,
        description="Standard deviation of pixel values; proxy for contrast",
    )
    sharpness_laplacian_variance: float = Field(
        ge=0.0,
        description="Variance of the Laplacian; higher means sharper",
    )
