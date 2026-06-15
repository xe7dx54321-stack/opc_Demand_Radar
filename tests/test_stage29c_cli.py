"""Tests for Stage 2.9C CLI (run-stage29c)."""
from __future__ import annotations
import pytest

from pathlib import Path

from typer.testing import CliRunner

from demand_radar.cli import app

runner = CliRunner()


def test_run_stage29c_help():
    result = runner.invoke(app, ["run-stage29c", "--help"])
    assert result.exit_code == 0
    assert "stage29c" in result.output.lower() or "2.9" in result.output or "calibrat" in result.output.lower()


def test_run_stage29c_command_exists():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "run-stage29c" in result.output


def test_calibrate_llm_command_exists():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "calibrate-llm-semantic-merge" in result.output


def test_build_llm_calibration_report_command_exists():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "build-llm-calibration-report" in result.output


@pytest.mark.slow
def test_run_stage29c_fake_llm(tmp_path: Path):
    """run-stage29c with fake LLM should produce calibrated output files."""
    if not Path("data/processed/cluster_merge_candidates.jsonl").exists():
        pytest.skip("Merge candidates not available")

    import shutil
    # Backup calibrated groups before the test overwrites them
    cal_path = Path("data/processed/calibrated_llm_ai_reviewed_cluster_groups.jsonl")
    backup = None
    if cal_path.exists():
        backup = tmp_path / "backup_calibrated.jsonl"
        shutil.copy2(cal_path, backup)

    try:
        result = runner.invoke(
            app,
            ["run-stage29c", "--fake-llm"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert Path("data/processed/calibrated_llm_semantic_merge_judgments.jsonl").exists()
        assert Path("data/processed/calibrated_llm_ai_reviewed_cluster_groups.jsonl").exists()
        assert Path("outputs/llm_semantic_merge_calibration_report.md").exists()
    finally:
        # Restore the real calibrated groups after the test
        if backup is not None and backup.exists():
            shutil.copy2(backup, cal_path)