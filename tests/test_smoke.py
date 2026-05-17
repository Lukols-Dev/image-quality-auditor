"""Smoke tests verifying baseline package integrity.

These tests validate that the package builds, installs, and imports
correctly. They serve as the first line of defense against broken
infrastructure (missing dependencies, malformed __init__.py, incorrect
src/ layout configuration).

While they will be supplemented by feature-specific tests as the
codebase grows, smoke tests are kept as permanent infrastructure
tests — they catch issues that unit tests cannot.
"""

from __future__ import annotations


class TestPackageInfrastructure:
    """Verify the package is correctly installed and importable."""

    def test_package_can_be_imported(self) -> None:
        """The package must import without errors.

        Catches: missing dependencies, syntax errors in __init__.py,
        incorrect src/ layout, missing __init__.py files.
        """
        import image_quality_auditor

        assert image_quality_auditor is not None

    def test_package_has_main_entry_point(self) -> None:
        """The CLI entry point must be accessible.

        Per pyproject.toml [project.scripts], 'image-quality-auditor'
        command maps to image_quality_auditor:main. This test verifies
        the symbol exists.
        """
        from image_quality_auditor import main

        assert callable(main), "main must be callable"
