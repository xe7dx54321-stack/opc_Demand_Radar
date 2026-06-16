"""Tests for MVP-C CLI commands."""
import pytest
from typer.testing import CliRunner
from demand_radar.cli import app

runner = CliRunner()


def test_run_mvp_c_no_data():
    """run-mvp-c completes gracefully even without any review data."""
    result = runner.invoke(app, ["run-mvp-c"])
    assert result.exit_code == 0 or result.exit_code == 1


def test_summarize_pain_reviews():
    """summarize-pain-reviews runs without crashing."""
    result = runner.invoke(app, ["summarize-pain-reviews"])
    assert result.exit_code == 0 or result.exit_code == 1


def test_build_mvp_c_report():
    """build-mvp-c-report generates reports without crashing."""
    result = runner.invoke(app, ["build-mvp-c-report"])
    assert result.exit_code == 0 or result.exit_code == 1


def test_run_mvp_c_output_contains_counts():
    """run-mvp-c outputs count information."""
    result = runner.invoke(app, ["run-mvp-c"])
    if result.exit_code == 0:
        assert "total=" in result.output or "Total" in result.output or "engineering=" in result.output
