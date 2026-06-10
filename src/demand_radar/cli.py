"""Typer CLI for Stage 1 Demand Radar."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from demand_radar.cleaning.text_cleaner import normalize_signals
from demand_radar.config.load_config import load_configs
from demand_radar.intake.manual_import import import_file
from demand_radar.loops.pain_extraction_loop import run_pain_extraction
from demand_radar.reporting.pain_points_report import build_pain_points_report
from demand_radar.state.raw_store import ensure_jsonl_file


app = typer.Typer(help="Domain-Bounded Demand Radar Stage 1 CLI.")

RUNTIME_FILES = [
    Path("data/raw/raw_signals.jsonl"),
    Path("data/processed/normalized_signals.jsonl"),
    Path("data/processed/pain_points.jsonl"),
    Path("data/quarantine/invalid_outputs.jsonl"),
    Path("outputs/pain_points_report.md"),
    Path("outputs/run_summary.json"),
]


@app.command()
def init(reset: Annotated[bool, typer.Option(help="Clear Stage 1 runtime files.")] = False) -> None:
    """Create required directories and empty runtime files."""

    for directory in ["configs", "data/raw", "data/processed", "data/quarantine", "outputs", "prompts", "examples"]:
        Path(directory).mkdir(parents=True, exist_ok=True)
    for path in RUNTIME_FILES:
        if reset or not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("", encoding="utf-8")
    ensure_jsonl_file("data/raw/raw_signals.jsonl")
    configs = load_configs("configs")
    typer.echo(f"Initialized Stage 1 workspace. Loaded configs: {', '.join(configs.keys())}")


@app.command("import")
def import_command(
    file: Annotated[Path, typer.Option("--file", exists=True, readable=True, help="CSV or JSONL file to import.")],
) -> None:
    """Import manual CSV or JSONL signals into Raw State."""

    imported = import_file(file)
    typer.echo(f"Imported {len(imported)} raw signals -> data/raw/raw_signals.jsonl")


@app.command()
def normalize() -> None:
    """Normalize Raw State into Working State."""

    normalized = normalize_signals()
    typer.echo(f"Normalized {len(normalized)} signals -> data/processed/normalized_signals.jsonl")


@app.command("extract-pain")
def extract_pain() -> None:
    """Run the Stage 1 Pain Extraction Loop."""

    pain_points = run_pain_extraction()
    typer.echo(f"Extracted {len(pain_points)} valid pain points -> data/processed/pain_points.jsonl")


@app.command("build-pain-report")
def build_pain_report() -> None:
    """Build the Stage 1 pain points report."""

    summary = build_pain_points_report()
    typer.echo(
        "Built pain report -> outputs/pain_points_report.md "
        f"(pain_points={summary.pain_points}, quarantine={summary.quarantined_items})"
    )


@app.command("run-stage1")
def run_stage1(
    input: Annotated[Path, typer.Option("--input", exists=True, readable=True, help="CSV or JSONL input file.")],
) -> None:
    """Run init, import, normalize, extract-pain, and build-pain-report."""

    init(reset=True)
    imported = import_file(input)
    typer.echo(f"Imported {len(imported)} raw signals -> data/raw/raw_signals.jsonl")
    normalized = normalize_signals()
    typer.echo(f"Normalized {len(normalized)} signals -> data/processed/normalized_signals.jsonl")
    pain_points = run_pain_extraction()
    typer.echo(f"Extracted {len(pain_points)} valid pain points -> data/processed/pain_points.jsonl")
    summary = build_pain_points_report()
    typer.echo(
        "Built pain report -> outputs/pain_points_report.md "
        f"(raw={summary.raw_signals}, normalized={summary.normalized_signals}, "
        f"pain_points={summary.pain_points}, quarantine={summary.quarantined_items})"
    )


def main() -> None:
    app()


if __name__ == "__main__":
    main()
