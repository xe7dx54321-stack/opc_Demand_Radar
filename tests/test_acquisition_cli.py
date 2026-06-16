"""Tests for acquisition CLI commands."""
from __future__ import annotations
import pytest
from typer.testing import CliRunner
from demand_radar.cli import app

runner = CliRunner()


def test_run_acquisition_command_registered():
    result = runner.invoke(app, ["run-acquisition", "--help"])
    assert result.exit_code == 0
    assert "domain" in result.output.lower() or "acquisition" in result.output.lower()


def test_build_evidence_pack_draft_command_registered():
    result = runner.invoke(app, ["build-evidence-pack-draft", "--help"])
    assert result.exit_code == 0


def test_run_radar_command_registered():
    result = runner.invoke(app, ["run-radar", "--help"])
    assert result.exit_code == 0


def test_build_acquisition_report_command_registered():
    result = runner.invoke(app, ["build-acquisition-report", "--help"])
    assert result.exit_code == 0


def test_build_evidence_pack_draft_no_candidates(tmp_path, monkeypatch):
    """build-evidence-pack-draft exits 0 when no candidates available."""
    import demand_radar.acquisition.acquisition_store as store_mod
    monkeypatch.setattr(store_mod, "_CANDIDATES_PATH", tmp_path / "nonexistent.jsonl")
    result = runner.invoke(app, ["build-evidence-pack-draft"])
    assert result.exit_code == 0
    assert "No evidence candidates" in result.output
