"""Application configuration via environment variables.

Uses Pydantic Settings to load configuration from environment variables
(prefix NEUROFACE_) and an optional .env file. This follows the
12-factor app principle: configuration lives in the environment, not
in code, so the same binary runs across dev/staging/prod.

Thresholds here drive the quality classification performed in scanner.py.
Defaults are chosen as sensible starting points based on typical uint8
image characteristics; override via environment as needed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuditorConfig(BaseSettings):
    """Configuration for an audit run.

    All values can be overridden via environment variables prefixed with
    NEUROFACE_ (e.g., NEUROFACE_MIN_BRIGHTNESS=25) or via a .env file.

    Attributes are grouped into quality thresholds, size requirements,
    output settings, and operational settings.
    """

    model_config = SettingsConfigDict(
        env_prefix="NEUROFACE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ----------------------------------------------------------
    # Quality thresholds (drive classifivation)
    # ----------------------------------------------------------

    min_brightness: float = Field(
        default=30.0,
        ge=0.0,
        le=255.0,
        description="Below this mean brightness, an image is underexposed",
    )

    max_brightness: float = Field(
        default=225.0,
        ge=0.0,
        le=255.0,
        description="Above this mean brightness, an image is overexposed",
    )

    min_contrast: float = Field(
        default=20.0,
        ge=0.0,
        description="Below this contrast (std dev), an image is too flat",
    )

    min_sharpness: float = Field(
        default=100.0,
        ge=0.0,
        description="Below this Laplacian variance, an image is too blurry",
    )

    # ----------------------------------------------------------
    # Size requirements
    # ----------------------------------------------------------
    min_width: int = Field(
        default=640,
        gt=0,
        description="Minimum acceptable image width in pixels",
    )
    min_height: int = Field(
        default=480,
        gt=0,
        description="Minimum acceptable image height in pixels",
    )
    max_file_size_mb: float = Field(
        default=50.0,
        gt=0.0,
        description="Maximum file size in MB (guards against decompression attacks)",
    )

    # ----------------------------------------------------------
    # Output settings
    # ----------------------------------------------------------
    output_dir: Path = Field(
        default=Path("./output"),
        description="Directory where reports (CSV, HTML) are written",
    )
    allowed_formats: tuple[str, ...] = Field(
        default=("JPEG", "PNG", "BMP", "TIFF", "WEBP"),
        description="Image formats accepted by the scanner",
    )

    # ----------------------------------------------------------
    # Operational settings
    # ----------------------------------------------------------
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )

    @model_validator(mode="after")
    def brightness_range_is_valid(self) -> Self:
        """Ensure min_brightness is strictly below max_brightness."""
        if self.min_brightness >= self.max_brightness:
            msg = (
                f"min_brightness ({self.min_brightness}) must be less than "
                f"max_brightness ({self.max_brightness})"
            )
            raise ValueError(msg)
        return self

    @property
    def max_file_size_bytes(self) -> int:
        """Maximum file size expressed in bytes."""
        return int(self.max_file_size_mb * 1024 * 1024)
