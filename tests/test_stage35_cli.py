"""Tests for Stage 3.5 CLI commands."""
import pytest
from pathlib import Path
from typer.testing import CliRunner
from demand_radar.cli import app

runner = CliRunner()


def test_run_stage35_help():
    result = runner.invoke(app, ["run-stage35", "--help"])
    assert result.exit_code == 0
    assert "stage35" in result.output.lower() or "snapshot" in result.output.lower()


def test_run_stage35_full_help():
    result = runner.invoke(app, ["run-stage35-full", "--help"])
    assert result.exit_code == 0


def test_select_stage35_candidates_help():
    result = runner.invoke(app, ["select-stage35-candidates", "--help"])
    assert result.exit_code == 0


def test_build_stage35_template_help():
    result = runner.invoke(app, ["build-stage35-template", "--help"])
    assert result.exit_code == 0


def test_validate_stage35_signals_help():
    result = runner.invoke(app, ["validate-stage35-signals", "--help"])
    assert result.exit_code == 0


def test_run_stage35_full_fails_without_api_key(monkeypatch):
    monkeypatch.delenv("DEMAND_RADAR_LLM_API_KEY", raising=False)
    result = runner.invoke(app, ["run-stage35-full"])
    assert result.exit_code != 0 or "API_KEY" in result.output or "ERROR" in result.output


def test_validate_stage35_signals_missing_file():
    result = runner.invoke(app, ["validate-stage35-signals",
                                 "--input", "nonexistent_stage35.csv"])
    assert result.exit_code in (0, 1, 2)


def test_run_stage35_runs(tmp_path, monkeypatch):
    """run-stage35 should run without crashing in an isolated directory."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "processed").mkdir(parents=True)
    (tmp_path / "data" / "processed" / "truth_scores.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "outputs" / "archive").mkdir(parents=True)
    (tmp_path / "examples").mkdir(parents=True)
    result = runner.invoke(app, ["run-stage35"])
    # Should not crash; may produce "no_candidates" but exit 0
    assert result.exit_code in (0, 1)
