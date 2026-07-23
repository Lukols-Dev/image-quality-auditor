"""Unit tests for report generation.

compute_summary is tested as pure computation over constructed records.
The write_* functions are tested against tmp_path: file is created, content
has the expected shape, and corrupted records degrade gracefully.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from image_quality_auditor.models import (
    AuditResult,
    ImageMetadata,
    ImageMetrics,
    QualityCategory,
)
from image_quality_auditor.reporter import (
    _COLUMNS,
    _to_row,
    compute_summary,
    write_csv,
    write_html,
    write_json,
)


def _image(
    category: QualityCategory,
    brightness: float | None = None,
    name: str = "photo.jpg",
) -> ImageMetadata:
    """Build a minimal record; brightness=None means no metrics."""
    metrics = None
    if brightness is not None:
        metrics = ImageMetrics(
            mean_brightness=brightness,
            contrast_std=40.0,
            sharpness_laplacian_variance=500.0,
        )
    return ImageMetadata(
        file_path=Path(f"/photos/{name}"),
        filename_original=name,
        filename_anonymized="a1b2c3d4e5f6a7b8.jpg",
        file_size_bytes=2048,
        file_format="JPEG",
        metrics=metrics,
        quality_category=category,
        error=None if brightness is not None else "decode failed",
    )


def _mixed() -> list[ImageMetadata]:
    """Two good, one poor, one corrupted."""
    return [
        _image(QualityCategory.GOOD, 100.0, "a.jpg"),
        _image(QualityCategory.GOOD, 200.0, "b.jpg"),
        _image(QualityCategory.POOR, 20.0, "c.jpg"),
        _image(QualityCategory.CORRUPTED, None, "d.jpg"),
    ]


def _result() -> AuditResult:
    images = _mixed()
    return AuditResult(
        images=tuple(images),
        summary=compute_summary(images, duration_seconds=1.5),
    )


class TestComputeSummary:
    """Tests for aggregate statistics."""

    def test_total_counts_every_image(self) -> None:
        """total_files_scanned includes corrupted images."""
        assert compute_summary(_mixed(), 1.0).total_files_scanned == 4

    def test_category_counts(self) -> None:
        """Each category is counted correctly."""
        counts = compute_summary(_mixed(), 1.0).counts
        assert counts.good == 2
        assert counts.poor == 1
        assert counts.corrupted == 1
        assert counts.acceptable == 0

    def test_averages_exclude_corrupted(self) -> None:
        """Averages are computed over decoded images only."""
        summary = compute_summary(_mixed(), 1.0)
        # (100 + 200 + 20) / 3, corrupted excluded
        assert summary.mean_brightness_avg == pytest.approx(106.667, abs=0.01)

    def test_empty_list(self) -> None:
        """An empty list yields zero counts and None averages."""
        summary = compute_summary([], 0.0)
        assert summary.total_files_scanned == 0
        assert summary.counts.total == 0
        assert summary.mean_brightness_avg is None

    def test_all_corrupted(self) -> None:
        """When nothing decoded, all averages are None."""
        images = [_image(QualityCategory.CORRUPTED) for _ in range(3)]
        summary = compute_summary(images, 0.5)
        assert summary.counts.corrupted == 3
        assert summary.mean_brightness_avg is None
        assert summary.contrast_std_avg is None
        assert summary.sharpness_avg is None

    def test_duration_passed_through(self) -> None:
        """duration_seconds is stored as given."""
        assert compute_summary([], 12.5).duration_seconds == 12.5


class TestToRow:
    """Tests for flattening a record into a CSV row."""

    def test_keys_match_columns(self) -> None:
        """Every row has exactly the declared columns."""
        row = _to_row(_image(QualityCategory.GOOD, 128.0))
        assert set(row.keys()) == set(_COLUMNS)

    def test_corrupted_row_has_none_metrics(self) -> None:
        """Corrupted records keep metric keys with None values."""
        row = _to_row(_image(QualityCategory.CORRUPTED))
        assert row["mean_brightness"] is None
        assert row["width"] is None
        assert row["error"] == "decode failed"

    def test_original_filename_not_included(self) -> None:
        """The original (identifying) filename must not leak into rows."""
        row = _to_row(_image(QualityCategory.GOOD, 128.0, "patient_001.jpg"))
        assert "patient_001" not in str(row.values())


class TestWriteCsv:
    """Tests for CSV output."""

    def test_creates_file(self, tmp_path: Path) -> None:
        """The output file is written."""
        path = tmp_path / "audit.csv"
        write_csv(_mixed(), path)
        assert path.exists()

    def test_creates_missing_parent_dirs(self, tmp_path: Path) -> None:
        """Nested output directories are created."""
        path = tmp_path / "deep" / "nested" / "audit.csv"
        write_csv(_mixed(), path)
        assert path.exists()

    def test_header_and_row_count(self, tmp_path: Path) -> None:
        """Output has a header plus one row per image."""
        path = tmp_path / "audit.csv"
        write_csv(_mixed(), path)
        lines = path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 5  # header + 4 images
        assert lines[0].split(",") == list(_COLUMNS)

    def test_empty_list_writes_header_only(self, tmp_path: Path) -> None:
        """An empty scan still produces a valid CSV with a header."""
        path = tmp_path / "audit.csv"
        write_csv([], path)
        lines = path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1

    def test_missing_values_are_empty_cells(self, tmp_path: Path) -> None:
        """None values are written as empty cells, not the text 'None'."""
        path = tmp_path / "audit.csv"
        write_csv([_image(QualityCategory.CORRUPTED)], path)
        content = path.read_text(encoding="utf-8")
        assert "None" not in content


class TestWriteJson:
    """Tests for JSON output."""

    def test_creates_valid_json(self, tmp_path: Path) -> None:
        """Output parses as JSON with images and summary."""
        path = tmp_path / "audit.json"
        write_json(_result(), path)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "images" in data
        assert "summary" in data
        assert len(data["images"]) == 4

    def test_round_trip(self, tmp_path: Path) -> None:
        """The written JSON validates back into an equal AuditResult."""
        path = tmp_path / "audit.json"
        original = _result()
        write_json(original, path)
        restored = AuditResult.model_validate_json(path.read_text(encoding="utf-8"))
        assert restored == original


class TestWriteHtml:
    """Tests for HTML output."""

    def test_creates_file(self, tmp_path: Path) -> None:
        """The report file is written."""
        path = tmp_path / "audit.html"
        write_html(_result(), path)
        assert path.exists()

    def test_contains_summary_counts(self, tmp_path: Path) -> None:
        """Summary numbers appear in the rendered page."""
        path = tmp_path / "audit.html"
        write_html(_result(), path)
        html = path.read_text(encoding="utf-8")
        assert "Image Quality Audit Report" in html
        assert "4 file(s) scanned" in html

    def test_contains_category_badges(self, tmp_path: Path) -> None:
        """Each image's category is rendered as a badge."""
        path = tmp_path / "audit.html"
        write_html(_result(), path)
        html = path.read_text(encoding="utf-8")
        assert "badge good" in html
        assert "badge corrupted" in html

    def test_empty_result(self, tmp_path: Path) -> None:
        """A scan with no images renders the empty-state message."""
        path = tmp_path / "audit.html"
        result = AuditResult(images=(), summary=compute_summary([], 0.0))
        write_html(result, path)
        assert "No images were scanned" in path.read_text(encoding="utf-8")

    def test_error_text_is_escaped(self, tmp_path: Path) -> None:
        """Untrusted text from error messages is HTML-escaped."""
        image = _image(QualityCategory.CORRUPTED)
        malicious = image.model_copy(update={"error": "<script>x</script>"})
        result = AuditResult(
            images=(malicious,),
            summary=compute_summary([malicious], 0.1),
        )
        path = tmp_path / "audit.html"
        write_html(result, path)
        html = path.read_text(encoding="utf-8")
        assert "<script>x</script>" not in html
        assert "&lt;script&gt;" in html
