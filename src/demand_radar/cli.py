"""Typer CLI for Stage 1 Demand Radar."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from demand_radar.calibration.calibration_review import append_calibration_review
from demand_radar.cleaning.text_cleaner import normalize_signals
from demand_radar.config.load_config import load_configs
from demand_radar.intake.manual_import import import_file
from demand_radar.loops.pain_extraction_loop import run_pain_extraction
from demand_radar.reporting.calibration_report import build_calibration_report
from demand_radar.reporting.pain_points_report import build_pain_points_report
from demand_radar.state.raw_store import ensure_jsonl_file


app = typer.Typer(help="Domain-Bounded Demand Radar Stage 1 CLI.")
calibration_review_app = typer.Typer(help="Human calibration review commands.")
app.add_typer(calibration_review_app, name="calibration-review")

RUNTIME_FILES = [
    Path("data/raw/raw_signals.jsonl"),
    Path("data/processed/normalized_signals.jsonl"),
    Path("data/processed/pain_points.jsonl"),
    Path("data/processed/calibration_reviews.jsonl"),
    Path("data/quarantine/invalid_outputs.jsonl"),
    Path("outputs/pain_points_report.md"),
    Path("outputs/calibration_report.md"),
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


@app.command("build-calibration-report")
def build_calibration_report_command() -> None:
    """Build the Stage 1.5 extraction calibration report."""

    summary = build_calibration_report()
    typer.echo(
        "Built calibration report -> outputs/calibration_report.md "
        f"(reviews={summary.calibration_reviews}, pain_points={summary.pain_points}, "
        f"quarantine={summary.quarantined_items})"
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


@app.command("run-calibration")
def run_calibration(
    input: Annotated[Path, typer.Option("--input", exists=True, readable=True, help="CSV or JSONL input file.")],
) -> None:
    """Run the Stage 1.5 real-signal calibration pipeline."""

    init(reset=True)
    imported = import_file(input)
    typer.echo(f"Imported {len(imported)} raw signals -> data/raw/raw_signals.jsonl")
    normalized = normalize_signals()
    typer.echo(f"Normalized {len(normalized)} signals -> data/processed/normalized_signals.jsonl")
    pain_points = run_pain_extraction()
    typer.echo(f"Extracted {len(pain_points)} valid pain points -> data/processed/pain_points.jsonl")
    pain_summary = build_pain_points_report()
    typer.echo(
        "Built pain report -> outputs/pain_points_report.md "
        f"(raw={pain_summary.raw_signals}, normalized={pain_summary.normalized_signals}, "
        f"pain_points={pain_summary.pain_points}, quarantine={pain_summary.quarantined_items})"
    )
    calibration_summary = build_calibration_report()
    typer.echo(
        "Built calibration report -> outputs/calibration_report.md "
        f"(reviews={calibration_summary.calibration_reviews})"
    )


@calibration_review_app.command("add")
def add_calibration_review(
    raw_signal_id: Annotated[str, typer.Option("--raw-signal-id", help="Raw signal ID under review.")],
    label: Annotated[str, typer.Option("--label", help="Calibration label.")],
    note: Annotated[str, typer.Option("--note", help="Human reviewer note.")],
    normalized_signal_id: Annotated[str | None, typer.Option("--normalized-signal-id")] = None,
    pain_point_id: Annotated[str | None, typer.Option("--pain-point-id")] = None,
    expected_persona: Annotated[str | None, typer.Option("--expected-persona")] = None,
    expected_evidence_quote: Annotated[str | None, typer.Option("--expected-evidence-quote")] = None,
    expected_pain_description: Annotated[str | None, typer.Option("--expected-pain-description")] = None,
    should_be_quarantined: Annotated[bool | None, typer.Option("--should-be-quarantined")] = None,
) -> None:
    """Append a human calibration review record."""

    review = append_calibration_review(
        raw_signal_id=raw_signal_id,
        normalized_signal_id=normalized_signal_id,
        pain_point_id=pain_point_id,
        label=label,
        reviewer_note=note,
        expected_persona=expected_persona,
        expected_evidence_quote=expected_evidence_quote,
        expected_pain_description=expected_pain_description,
        should_be_quarantined=should_be_quarantined,
    )
    typer.echo(f"Added calibration review {review.review_id} -> data/processed/calibration_reviews.jsonl")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
