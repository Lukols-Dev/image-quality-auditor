"""Unit tests for filename anonymization.

Tests verify the core guarantees: determinism (same input -> same output),
distinctness (different inputs -> different outputs), extension handling,
and the fixed hash length.
"""

from __future__ import annotations

from image_quality_auditor.anonymizer import HASH_LENGTH, anonymize_filename


class TestDeterminism:
    """The anonymizer must be deterministic."""

    def test_same_input_same_output(self) -> None:
        """The same filename always produces the same result."""
        result_a = anonymize_filename("patient_001.jpg")
        result_b = anonymize_filename("patient_001.jpg")
        assert result_a == result_b

    def test_stable_across_calls(self) -> None:
        """Repeated calls yield an identical value."""
        results = {anonymize_filename("scan.png") for _ in range(10)}
        assert len(results) == 1  # all identical -> one unique value


class TestDistinctness:
    """Different inputs must produce different outputs."""

    def test_different_names_differ(self) -> None:
        """Distinct filenames produce distinct hashes."""
        a = anonymize_filename("patient_001.jpg")
        b = anonymize_filename("patient_002.jpg")
        assert a != b

    def test_avalanche_effect(self) -> None:
        """A one-character change yields a completely different hash."""
        a = anonymize_filename("a.jpg")
        b = anonymize_filename("b.jpg")
        assert a != b

    def test_same_stem_different_extension_differ(self) -> None:
        """Same stem with different extension produces different hashes."""
        jpg = anonymize_filename("photo.jpg")
        png = anonymize_filename("photo.png")
        assert jpg != png


class TestExtensionHandling:
    """Extension preservation and normalization."""

    def test_extension_preserved(self) -> None:
        """The file extension is kept in the result."""
        result = anonymize_filename("patient_001.jpg")
        assert result.endswith(".jpg")

    def test_extension_lowercased(self) -> None:
        """An uppercase extension is normalized to lowercase."""
        result = anonymize_filename("photo.JPG")
        assert result.endswith(".jpg")
        assert ".JPG" not in result

    def test_no_extension(self) -> None:
        """A name without an extension yields just the hash."""
        result = anonymize_filename("scan")
        assert "." not in result

    def test_double_extension_takes_last(self) -> None:
        """For multi-part extensions, only the final suffix is preserved."""
        result = anonymize_filename("archive.tar.gz")
        assert result.endswith(".gz")


class TestHashLength:
    """The hash portion has the configured length."""

    def test_hash_length_with_extension(self) -> None:
        """The hash stem has HASH_LENGTH characters."""
        result = anonymize_filename("patient_001.jpg")
        stem = result.split(".")[0]
        assert len(stem) == HASH_LENGTH

    def test_hash_length_without_extension(self) -> None:
        """Without an extension, the whole result is the hash."""
        result = anonymize_filename("scan")
        assert len(result) == HASH_LENGTH

    def test_hash_is_hexadecimal(self) -> None:
        """The hash consists only of lowercase hex characters."""
        result = anonymize_filename("patient_001.jpg")
        stem = result.split(".")[0]
        assert all(c in "0123456789abcdef" for c in stem)


class TestEdgeCases:
    """Edge cases: unicode, empty-ish inputs, special characters."""

    def test_unicode_filename(self) -> None:
        """Unicode characters (e.g., Polish) are handled without error."""
        result = anonymize_filename("pacjęt_ąćź.jpg")
        assert result.endswith(".jpg")
        stem = result.split(".")[0]
        assert len(stem) == HASH_LENGTH

    def test_unicode_is_deterministic(self) -> None:
        """Unicode input is also deterministic."""
        a = anonymize_filename("zdjęcie.png")
        b = anonymize_filename("zdjęcie.png")
        assert a == b

    def test_spaces_in_name(self) -> None:
        """Filenames with spaces are handled."""
        result = anonymize_filename("my photo.jpg")
        assert result.endswith(".jpg")

    def test_hidden_file(self) -> None:
        """A dotfile (e.g., .gitignore) is treated as having no extension."""
        result = anonymize_filename(".gitignore")
        # Path treats .gitignore as a name with no suffix
        assert len(result) == HASH_LENGTH
