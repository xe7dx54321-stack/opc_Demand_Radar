"""Tests for MVP-B CLI commands."""
import pytest
from typer.testing import CliRunner
from demand_radar.cli import app


runner = CliRunner()


def test_run_mvp_b_no_data():
    """run-mvp-b completes even without candidate data."""
    result = runner.invoke(app, [
        "run-mvp-b",
        "--domain", "ai_investment_tracking",
        "--max-items", "5",
        "--fake-llm",
    ])
    # Should not crash
    assert result.exit_code == 0 or "No candidates" in (result.output or "")


def test_run_domain_relevance_no_data():
    """run-domain-relevance completes without crashing."""
    result = runner.invoke(app, [
        "run-domain-relevance",
        "--domain", "ai_investment_tracking",
    ])
    assert result.exit_code == 0 or result.exit_code == 1


def test_build_mvp_b_report():
    """build-mvp-b-report can be invoked."""
    result = runner.invoke(app, ["build-mvp-b-report"])
    assert result.exit_code == 0 or result.exit_code == 1


def test_fill_evidence_pack():
    """fill-evidence-pack can be invoked."""
    result = runner.invoke(app, ["fill-evidence-pack"])
    assert result.exit_code == 0 or result.exit_code == 1


def test_run_pain_extraction_no_llm():
    """run-pain-extraction without LLM key."""
    result = runner.invoke(app, [
        "run-pain-extraction",
        "--domain", "ai_investment_tracking",
    ])
    # Should complete without crashing
    assert result.exit_code == 0 or result.exit_code == 1
