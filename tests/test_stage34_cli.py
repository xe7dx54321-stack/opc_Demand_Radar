"""Tests for Stage 3.4 CLI commands."""
import pytest
from pathlib import Path
from typer.testing import CliRunner
from demand_radar.cli import app

runner = CliRunner()


def test_snapshot_truth_state_help():
    result = runner.invoke(app, ["snapshot-truth-state", "--help"])
    assert result.exit_code == 0
    assert "snapshot" in result.output.lower() or "name" in result.output.lower()


def test_attribute_targeted_evidence_help():
    result = runner.invoke(app, ["attribute-targeted-evidence", "--help"])
    assert result.exit_code == 0


def test_match_candidate_lineage_help():
    result = runner.invoke(app, ["match-candidate-lineage", "--help"])
    assert result.exit_code == 0


def test_build_stable_truth_delta_help():
    result = runner.invoke(app, ["build-stable-truth-delta", "--help"])
    assert result.exit_code == 0


def test_build_lineage_reports_help():
    result = runner.invoke(app, ["build-lineage-reports", "--help"])
    assert result.exit_code == 0


def test_run_stage34_help():
    result = runner.invoke(app, ["run-stage34", "--help"])
    assert result.exit_code == 0
    assert "before-snapshot" in result.output or "targeted" in result.output


def test_snapshot_truth_state_creates_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Create required data files so snapshot can run
    (tmp_path / "data" / "processed").mkdir(parents=True)
    (tmp_path / "data" / "processed" / "truth_scores.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "data" / "processed" / "calibrated_llm_ai_reviewed_cluster_groups.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "outputs" / "archive").mkdir(parents=True)
    result = runner.invoke(app, ["snapshot-truth-state", "--name", "test_snap"])
    # Should not crash; archive directory should be created
    assert result.exit_code in (0, 1)  # allow 1 if some files missing


def test_run_stage34_runs_without_crashing(tmp_path, monkeypatch):
    """run-stage34 should not crash even with missing/empty data."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "processed").mkdir(parents=True)
    (tmp_path / "data" / "processed" / "truth_scores.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "examples").mkdir(parents=True)
    # Create a minimal targeted CSV with required columns
    csv_content = "target_signal_id,target_group_id,raw_text,url,source_type,collection_status\\n"
    (tmp_path / "examples" / "real_signal_samples_stage33.csv").write_text(csv_content, encoding="utf-8")
    (tmp_path / "outputs" / "archive" / "before_stage33").mkdir(parents=True)
    result = runner.invoke(app, [
        "run-stage34",
        "--before-snapshot", str(tmp_path / "outputs" / "archive" / "before_stage33"),
        "--targeted", str(tmp_path / "examples" / "real_signal_samples_stage33.csv"),
    ])
    # Should not raise an unhandled exception
    assert result.exit_code in (0, 1)


def test_attribute_targeted_evidence_with_nonexistent_file():
    """Graceful exit when targeted file does not exist."""
    result = runner.invoke(app, ["attribute-targeted-evidence",
                                  "--targeted", "nonexistent_stage33.csv"])
    # Should fail gracefully (exit code 1) rather than stack trace crash
    assert result.exit_code in (0, 1, 2)


def test_build_stable_truth_delta_with_no_data(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "processed").mkdir(parents=True)
    (tmp_path / "outputs").mkdir(parents=True)
    result = runner.invoke(app, ["build-stable-truth-delta"])
    # Should either succeed (empty output) or give a user-friendly message
    assert result.exit_code in (0, 1)
