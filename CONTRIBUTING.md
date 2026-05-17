# Contributing

Thank you for considering a contribution. This document describes the
development workflow, quality standards, and PR process for this project.

## Development setup

### Prerequisites

- Python 3.13+ (managed by `uv` — installed automatically)
- [`uv`](https://github.com/astral-sh/uv) for dependency management
- Git

### One-time setup

\```bash

# Clone

git clone https://github.com/<your-username>/image-quality-auditor.git
cd image-quality-auditor

# Install dependencies (creates .venv automatically)

uv sync

# Install pre-commit hooks (commit-time + push-time checks)

uv run pre-commit install --hook-type pre-commit --hook-type pre-push
\```

You're ready to develop.

## Quality gates

Quality is enforced at multiple layers — fail fast, fail locally:

| Stage      | Trigger      | What runs                               | Time |
| ---------- | ------------ | --------------------------------------- | ---- |
| Editor     | On save      | Ruff format (via IDE plugin)            | <1s  |
| Pre-commit | `git commit` | Ruff lint+format, file sanity checks    | ~2s  |
| Pre-push   | `git push`   | Mypy (strict mode) on full codebase     | ~5s  |
| CI         | Pull request | All of the above + pytest with coverage | ~30s |

**Single source of truth**: all tool configurations live in `pyproject.toml`.
Pre-commit and CI delegate to those configs — no duplication.

## Running checks manually

\```bash

# Format code

uv run ruff format

# Lint (with auto-fixes)

uv run ruff check --fix

# Type check

uv run mypy src tests

# Run tests

uv run pytest

# Run tests with coverage report (HTML in htmlcov/)

uv run pytest --cov

# Run all pre-commit hooks manually

uv run pre-commit run --all-files
\```

## Project structure

\```
image-quality-auditor/
├── src/image_quality_auditor/ # Main package
│ ├── cli.py # Click CLI entry point
│ ├── config.py # Pydantic Settings (env-driven)
│ ├── models.py # Domain models (Pydantic)
│ ├── scanner.py # Folder traversal + file validation
│ ├── metrics.py # Quality metrics (brightness, sharpness)
│ ├── anonymizer.py # Filename anonymization (SHA256)
│ └── reporter.py # CSV + HTML report generation
├── tests/ # Pytest test suite
├── templates/ # Jinja2 templates (HTML report)
├── pyproject.toml # Project metadata, dependencies, tool configs
├── .pre-commit-config.yaml # Pre-commit hooks (delegates to pyproject.toml)
└── uv.lock # Pinned dependency versions
\```

## Branching strategy

- `main` — stable, deployable. Protected branch.
- `feat/<short-name>` — new features (e.g. `feat/parallel-scanner`)
- `fix/<short-name>` — bug fixes (e.g. `fix/corrupt-png-handling`)
- `refactor/<short-name>` — internal restructuring
- `docs/<short-name>` — documentation only
- `chore/<short-name>` — tooling, dependencies, no behavior change

## Commit messages

This project follows [Conventional Commits](https://www.conventionalcommits.org/):

\```
<type>: <short summary>

[optional body explaining what and why, not how]

[optional footer: BREAKING CHANGE, refs issues]
\```

**Types:**

- `feat:` new user-facing feature
- `fix:` bug fix
- `refactor:` code restructure with no behavior change
- `test:` adding or modifying tests
- `docs:` documentation only
- `chore:` tooling, dependencies, build config
- `perf:` performance improvement
- `style:` formatting only (rare — usually auto-applied)

**Examples:**

\```
feat: add parallel image processing with multiprocessing pool

Processing 10k images now takes ~30s instead of ~5min on a 8-core machine.
Pool size defaults to cpu_count(), configurable via NEUROFACE_WORKERS env var.
\```

\```
fix: handle truncated JPEG files without crashing scanner

Pillow raises OSError on truncated JPEGs. Now caught and classified
as 'corrupted' quality category with original error preserved in metadata.
\```

## Pull request process

1. **Branch from `main`** following the naming convention above
2. **Make changes** — keep commits small and focused (one concern per commit)
3. **Ensure quality gates pass locally**:
   \```bash
   uv run pre-commit run --all-files
   uv run pytest
   \```
4. **Open PR** with:
   - Clear title (follows commit convention)
   - Description: what changed, why, any tradeoffs
   - Link to related issues if any
5. **Wait for CI** to pass + review
6. **Squash merge** to `main` (keeps history clean)

## Testing standards

- New features require corresponding tests
- Aim for >80% coverage (enforced in CI)
- Tests should be **isolated** (no shared state, no network, no large fixtures)
- Use `tmp_path` and `tmp_path_factory` for filesystem tests
- Mock external dependencies (filesystem, OpenCV) when testing logic in isolation

## Reporting bugs

Open an issue with:

- Reproduction steps
- Expected vs actual behavior
- Python version (`python --version`)
- Library versions (`uv pip list`)
- Sample input that triggers the bug (if possible)

## Reporting security vulnerabilities

**Do not open public issues for security concerns.** See [SECURITY.md](SECURITY.md).
