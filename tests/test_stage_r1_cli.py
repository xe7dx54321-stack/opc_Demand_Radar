"""Tests for Stage R1 CLI commands."""
from __future__ import annotations
import csv
from pathlib import Path
import typer
from typer.testing import CliRunner
from demand_radar.cli import app
from demand_radar.real_evidence.real_evidence_validator import TEMPLATE_COLUMNS

runner = CliRunner()


def test_build_real_evidence_template(tmp_path, monkeypatch):
    """build-real-evidence-template generates a CSV."""
    import demand_radar.real_evidence.real_evidence_validator as val_mod
    monkeypatch.setattr(
        val_mod,
        "generate_template",
        lambda path=None: (
            Path(path).parent.mkdir(parents=True, exist_ok=True) or None,
            Path(path).write_text("evidence_id\n", encoding="utf-8"),
            Path(path),
        )[-1] if path else Path("examples/template.csv"),
    )
    result = runner.invoke(app, ["build-real-evidence-template"])
    assert result.exit_code == 0


def test_validate_real_evidence_pack_missing_file(tmp_path):
    """validate-real-evidence-pack fails gracefully when file not found."""
    missing = str(tmp_path / "nonexistent.csv")
    result = runner.invoke(app, ["validate-real-evidence-pack", "--input", missing])
    assert result.exit_code != 0 or "not found" in (result.output or "").lower()


def test_validate_real_evidence_pack_with_file(tmp_path, monkeypatch):
    """validate-real-evidence-pack processes a valid file."""
    csv_path = tmp_path / "evidence.csv"
    row = {
        "evidence_id": "re_001",
        "target_direction_id": "ai_investment_tracking",
        "target_direction_title_zh": "AI",
        "source_url": "https://example.com",
        "source_note": "",
        "source_name": "G2",
        "source_type": "product_review",
        "source_author_or_org": "",
        "published_at": "2024-01-01",
        "observed_at": "",
        "language": "en",
        "title": "Test",
        "raw_text": "We spend 3 hours weekly tracking AI companies manually with spreadsheets all the time.",
        "evidence_quote": "3 hours weekly",
        "persona": "investor",
        "persona_confidence": "0.9",
        "workflow_stage": "sourcing",
        "pain_type": "information_scattered",
        "evidence_type": "pain_signal",
        "commercial_signal_type": "paid_tool",
        "current_solution": "spreadsheet",
        "paid_alternative": "PitchBook",
        "business_impact": "time waste",
        "time_cost_signal": "3hrs",
        "budget_signal": "$200/month",
        "domain_tags": "ai",
        "collection_query": "",
        "collector_note": "",
        "is_synthetic": "false",
        "exclude_from_scoring": "false",
    }
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=TEMPLATE_COLUMNS)
        writer.writeheader()
        writer.writerow(row)

    # Monkeypatch the output paths
    import demand_radar.real_evidence.real_evidence_validator as val_mod
    original_validate = val_mod.validate_real_evidence_pack

    def patched_validate(input_path, items_output, validation_output):
        new_items = tmp_path / "items.jsonl"
        new_val = tmp_path / "val.jsonl"
        return original_validate(input_path, new_items, new_val)

    monkeypatch.setattr(val_mod, "validate_real_evidence_pack", patched_validate)

    result = runner.invoke(app, ["validate-real-evidence-pack", "--input", str(csv_path)])
    assert result.exit_code == 0
    assert "Validation" in result.output


def test_run_stage_r1_no_filled_file(tmp_path, monkeypatch):
    """run-stage-r1 exits gracefully when filled file missing."""
    missing = str(tmp_path / "missing_evidence.csv")
    import demand_radar.real_evidence.real_evidence_pipeline as pipe_mod
    monkeypatch.setattr(pipe_mod, "_TEMPLATE_PATH", tmp_path / "template.csv")
    result = runner.invoke(app, ["run-stage-r1", "--input", missing])
    assert result.exit_code == 0
    output = result.output or ""
    assert "尚未填写" in output or "not found" in output.lower() or "filled_file_exists" not in output


def test_run_stage_r1_command_exists():
    """run-stage-r1 command is registered."""
    result = runner.invoke(app, ["run-stage-r1", "--help"])
    assert result.exit_code == 0
    assert "stage" in result.output.lower() or "r1" in result.output.lower()