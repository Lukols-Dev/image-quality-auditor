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
