"""Shared test helpers.

Every test builds its configuration through make_config, which disables
.env loading so the suite is isolated from any local .env file.
"""

from __future__ import annotations

from typing import Any

from image_quality_auditor.config import AuditorConfig


def make_config(**overrides: Any) -> AuditorConfig:
    """Build an AuditorConfig with .env loading disabled.

    BaseSettings accepts `_env_file` at runtime, but mypy synthesizes
    AuditorConfig.__init__ from the model fields alone (pydantic's
    metaclass is @dataclass_transform-decorated), so the keyword is
    invisible to it. Suppress that once here rather than at every call.
    """
    return AuditorConfig(_env_file=None, **overrides)  # type: ignore[call-arg]
