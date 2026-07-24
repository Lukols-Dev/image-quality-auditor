from __future__ import annotations

import time
from pathlib import Path

import click

from image_quality_auditor.config import AuditorConfig
from image_quality_auditor.models import AuditResult
from image_quality_auditor.reporter import compute_summary, write_csv, write_html, write_json
from image_quality_auditor.scanner import scan_folder


@click.command()
@click.argument(
    "folder",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=None,
    help="Where to write reports. Overrides NEUROFACE_OUTPUT_DIR.",
)
@click.option(
    "--format",
    "formats",
    type=click.Choice(["csv", "json", "html"], case_sensitive=False),
    multiple=True,
    default=("csv",),
    help="Report format(s) to write. Repeat for multiple.",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="List every image, not just the summary.",
)
def audit(
    folder: Path,
    output_dir: Path | None,
    formats: tuple[str, ...],
    verbose: bool,
) -> None:
    """Audit image quality in FOLDER and write reports."""

    config = AuditorConfig(output_dir=output_dir) if output_dir is not None else AuditorConfig()

    click.echo("Start scanning")

    start = time.perf_counter()
    images = scan_folder(folder, config)
    duration = time.perf_counter() - start
    summary = compute_summary(images, duration_seconds=duration)

    click.echo(f"Scanned {summary.total_files_scanned} file(s) in {duration:.2f}s")
    click.secho(f"  good:       {summary.counts.good:>5}", fg="green")
    click.secho(f"  acceptable: {summary.counts.acceptable:>5}", fg="yellow")
    click.secho(f"  poor:       {summary.counts.poor:>5}", fg="red")
    click.secho(f"  corrupted:  {summary.counts.corrupted:>5}", fg="bright_black")
    click.echo(f"  usable:     {summary.counts.usable:>5}")

    if verbose:
        click.echo()
        for image in images:
            click.echo(f"  {image.filename_anonymized}  {image.quality_category.value}")

    result = AuditResult(images=tuple(images), summary=summary)

    if "csv" in formats:
        write_csv(images, config.output_dir / "audit.csv")
    if "json" in formats:
        write_json(result, config.output_dir / "audit.json")
    if "html" in formats:
        write_html(result, config.output_dir / "audit.html")
    if formats:
        click.echo(f"\nReports written to {config.output_dir}")
