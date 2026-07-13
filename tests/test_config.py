"""Unit tests for application configuration.

Tests cover defaults, environment-variable overrides, cross-field
validation, and computed properties. The _env_file=None argument
disables .env loading so tests are isolated from any local .env file.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from image_quality_auditor.config import AuditorConfig


class TestDefaults:
    """Tests for default configuration values."""

    def test_default_thresholds(self) -> None:
        """Quality thresholds have expected defaults."""
        config = AuditorConfig(_env_file=None)
        assert config.min_brightness == 30.0
        assert config.max_brightness == 225.0
        assert config.min_contrast == 20.0
        assert config.min_sharpness == 100.0

    def test_default_size_requirements(self) -> None:
        """Size requirements have expected defaults."""
        config = AuditorConfig(_env_file=None)
        assert config.min_width == 640
        assert config.min_height == 480
        assert config.max_file_size_mb == 50.0

    def test_default_output_settings(self) -> None:
        """Output settings have expected defaults."""
        config = AuditorConfig(_env_file=None)
        assert config.output_dir == Path("./output")
        assert "JPEG" in config.allowed_formats
        assert "PNG" in config.allowed_formats

    def test_default_log_level(self) -> None:
        """Log level defaults to INFO."""
        config = AuditorConfig(_env_file=None)
        assert config.log_level == "INFO"


class TestEnvironmentOverride:
    """Tests for environment-variable overrides."""

    def test_env_overrides_brightness(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """An environment variable overrides the default brightness."""
        monkeypatch.setenv("NEUROFACE_MIN_BRIGHTNESS", "50")
        config = AuditorConfig(_env_file=None)
        assert config.min_brightness == 50.0

    def test_env_overrides_width(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """An environment variable overrides the default width."""
        monkeypatch.setenv("NEUROFACE_MIN_WIDTH", "1024")
        config = AuditorConfig(_env_file=None)
        assert config.min_width == 1024

    def test_env_overrides_log_level(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """An environment variable overrides the log level."""
        monkeypatch.setenv("NEUROFACE_LOG_LEVEL", "DEBUG")
        config = AuditorConfig(_env_file=None)
        assert config.log_level == "DEBUG"

    def test_string_coerced_to_float(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Env var strings are coerced to the field's type."""
        monkeypatch.setenv("NEUROFACE_MAX_FILE_SIZE_MB", "25.5")
        config = AuditorConfig(_env_file=None)
        assert config.max_file_size_mb == 25.5
        assert isinstance(config.max_file_size_mb, float)


class TestConstructorOverride:
    """Tests for explicit constructor overrides."""

    def test_explicit_values(self) -> None:
        """Values passed to the constructor override defaults."""
        config = AuditorConfig(
            _env_file=None,
            min_brightness=40.0,
            min_width=800,
        )
        assert config.min_brightness == 40.0
        assert config.min_width == 800

    def test_partial_override_keeps_other_defaults(self) -> None:
        """Overriding one value leaves others at their defaults."""
        config = AuditorConfig(_env_file=None, min_brightness=40.0)
        assert config.min_brightness == 40.0
        assert config.max_brightness == 225.0  # still default


class TestValidation:
    """Tests for configuration validation rules."""

    def test_brightness_min_below_max_valid(self) -> None:
        """A valid brightness range (min < max) is accepted."""
        config = AuditorConfig(
            _env_file=None,
            min_brightness=30.0,
            max_brightness=200.0,
        )
        assert config.min_brightness < config.max_brightness

    def test_brightness_min_equals_max_rejected(self) -> None:
        """min_brightness equal to max_brightness is rejected."""
        with pytest.raises(ValidationError):
            AuditorConfig(
                _env_file=None,
                min_brightness=100.0,
                max_brightness=100.0,
            )

    def test_brightness_min_above_max_rejected(self) -> None:
        """min_brightness greater than max_brightness is rejected."""
        with pytest.raises(ValidationError):
            AuditorConfig(
                _env_file=None,
                min_brightness=200.0,
                max_brightness=100.0,
            )

    def test_brightness_out_of_range_rejected(self) -> None:
        """Brightness above 255 is rejected by the field constraint."""
        with pytest.raises(ValidationError):
            AuditorConfig(_env_file=None, min_brightness=300.0)

    def test_negative_width_rejected(self) -> None:
        """A non-positive width is rejected."""
        with pytest.raises(ValidationError):
            AuditorConfig(_env_file=None, min_width=0)

    def test_negative_file_size_rejected(self) -> None:
        """A non-positive max file size is rejected."""
        with pytest.raises(ValidationError):
            AuditorConfig(_env_file=None, max_file_size_mb=0.0)


class TestComputedProperties:
    """Tests for computed properties."""

    def test_max_file_size_bytes(self) -> None:
        """max_file_size_bytes converts MB to bytes (binary)."""
        config = AuditorConfig(_env_file=None, max_file_size_mb=1.0)
        assert config.max_file_size_bytes == 1_048_576  # 1 MB = 1024*1024

    def test_max_file_size_bytes_default(self) -> None:
        """Default 50 MB converts to the expected byte count."""
        config = AuditorConfig(_env_file=None)
        assert config.max_file_size_bytes == 52_428_800  # 50 * 1024 * 1024
