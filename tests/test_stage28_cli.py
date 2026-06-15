"""Tests for Stage 2.8 CLI run-stage28 command."""
from __future__ import annotations

import pytest
from pathlib import Path
from typer.testing import CliRunner

from demand_radar.cli import app

runner = CliRunner()


def test_run_stage28_help():
    result = runner.invoke(app, ["run-stage28", "--help"])
    assert result.exit_code == 0
    assert "run-stage28" in result.output


def test_run_stage28_command_exists():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "run-stage28" in result.output


@pytest.mark.slow
def test_stage28_runs_on_sample_data(tmp_path: Path):
    """run-stage28 with sample CSV produces key output files."""
    sample_csv = Path("examples/real_signal_samples_stage26.csv")
    if not sample_csv.exists():
        pytest.skip("Sample CSV not available")

    result = runner.invoke(
        app,
        ["run-stage28", "--input", str(sample_csv)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert Path("data/processed/semantic_merge_judgments.jsonl").exists()
    assert Path("data/processed/ai_reviewed_cluster_groups.jsonl").exists()
    assert Path("data/processed/human_exception_queue.jsonl").exists()
    assert Path("outputs/semantic_merge_judgment_report.md").exists()
    assert Path("outputs/ai_reviewed_cluster_groups_report.md").exists()
    assert Path("outputs/human_exception_queue_report.md").exists()
    assert Path("outputs/batch_summary_report.md").exists()
