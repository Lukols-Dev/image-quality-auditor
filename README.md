# image-quality-auditor

> Production-grade CLI tool for auditing image dataset quality before AI training.

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Code style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](http://mypy-lang.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Why this exists

In medical AI applications - like facial analysis for neurological assessment -
training data quality directly determines model reliability. A blurry photo, an
overexposed sample, or a corrupted file silently entering the training set can
degrade model performance in ways that only surface in production.

**This tool runs as a quality gate before training**: it scans an image folder,
computes objective quality metrics, anonymizes filenames, and produces both
machine-readable (CSV) and human-readable (HTML) reports.

Built as part of a Computer Vision portfolio focused on industrial and medical
imaging pipelines.

## What it does

- 📏 **Quality metrics**: mean brightness, contrast (pixel std-dev), sharpness
  (Laplacian variance)
- 🔍 **Validation**: detects corrupted, empty, or sub-resolution images
- 🔒 **Privacy**: SHA256-based filename anonymization for medical data compliance
- 📊 **Reporting**: CSV metadata + standalone HTML report with brightness histograms
- ⚡ **Performance**: parallel processing for large datasets

## Quick start

\```bash

# Clone and install

git clone https://github.com/<your-username>/image-quality-auditor.git
cd image-quality-auditor
uv sync

# Run on a folder of images

uv run image-quality-auditor ./photos --output ./report
\```

Output:

\```
./report/
├── metadata.csv # Per-image metrics and quality classification
├── report.html # Visual summary with histograms
└── audit.log # Run log
\```

## How quality is measured

| Metric         | Definition                   | Why it matters                |
| -------------- | ---------------------------- | ----------------------------- |
| **Brightness** | Mean pixel value (0-255)     | Under/overexposed images      |
| **Contrast**   | Standard deviation of pixels | Low-information flat images   |
| **Sharpness**  | Variance of Laplacian        | Blur detection                |
| **Resolution** | Width × height in pixels     | Minimum input size for models |

Each image is classified as `good`, `acceptable`, `poor`, or `corrupted`
based on configurable thresholds.

## Tech stack

- **Python 3.13+** with strict typing (`mypy --strict`)
- **Click** - CLI framework
- **Pydantic v2** - runtime data validation
- **OpenCV** - image processing primitives
- **NumPy** - vectorized metric computation
- **Pandas** - tabular data output
- **Jinja2** - HTML report templating

Development tooling: `uv` (packaging), `ruff` (lint+format), `pytest` (testing),
`pre-commit` (quality gates).

## Documentation

- [Contributing guide](CONTRIBUTING.md) — development setup, testing, PR process
- [Security policy](SECURITY.md) — vulnerability reporting

## License

[MIT](LICENSE) — free to use, modify, and distribute.

---

**Author:** Łukasz Olszewski · [GitHub](https://github.com/<your-username>) · Computer Vision portfolio
