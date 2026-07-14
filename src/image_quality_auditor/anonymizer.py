"""Filename anonymization for privacy compliance.

Converts original filenames into privacy-safe, deterministic hashes while
preserving the file extension. Original names may contain personal data
(patient names, identifiers), which must not leak into reports or logs
when handling medical images.

The anonymization is deterministic: the same input always produces the
same output. This allows tracking a given file across audit runs without
exposing its original name.
"""

import hashlib
from pathlib import Path

HASH_LENGTH = 16


def anonymize_filename(orginal: str) -> str:
    """Return a deterministic, privacy-safe filename for the given name.

    The original name (without extension) is hashed with SHA256; the first
    HASH_LENGTH hex characters form the new stem. The extension is preserved
    and normalized to lowercase.

    Args:
        original: The original filename, with or without an extension
            (e.g., "patient_001.JPG", "scan").

    Returns:
        An anonymized filename of the form "<hash>.<ext>", or "<hash>" when
        the original has no extension. The hash is derived from the full
        original name (stem + extension) for stability.

    Examples:
        >>> anonymize_filename("patient_001.jpg")  # doctest: +SKIP
        'a1b2c3d4e5f6a7b8.jpg'
        >>> anonymize_filename("scan.PNG")  # doctest: +SKIP
        'f0e1d2c3b4a59687.png'
    """

    path = Path(orginal)
    extension = path.suffix.lower()

    digest = hashlib.sha256(orginal.encode("utf-8")).hexdigest()
    hashed_stem = digest[:HASH_LENGTH]

    if extension:
        return f"{hashed_stem}{extension}"
    return hashed_stem
