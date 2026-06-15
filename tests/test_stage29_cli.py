"""Tests for Stage 2.9 CLI run-stage29 command."""
from __future__ import annotations

import pytest
from pathlib import Path
from typer.testing import CliRunner

from demand_radar.cli import app

runner = CliRunner()


def test_run_stage29_help():
    result = runner.invoke(app, ["run-stage29", "--help"])
    assert result.exit_code == 0
    assert "run-stage29" in result.output


def test_run_stage29_command_exists():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "run-stage29" in result.output


def test_llm_semantic_merge_judge_command_exists():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "llm-semantic-merge-judge" in result.output


def test_compare_semantic_merge_command_exists():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "compare-semantic-merge" in result.output


@pytest.mark.slow
def test_run_stage29_with_fake_llm_on_sample_data():
    """run-stage29 --fake-llm with sample CSV should produce llm_* output files."""
    sample_csv = Path("examples/real_signal_samples_stage26.csv")
    if not sample_csv.exists():
        pytest.skip("Sample CSV not available")

    result = runner.invoke(
        app,
        ["run-stage29", "--input", str(sample_csv), "--fake-llm"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, f"Output: {result.output}"
    assert Path("data/processed/llm_semantic_merge_judgments.jsonl").exists()
    assert Path("data/processed/llm_ai_reviewed_cluster_groups.jsonl").exists()
    assert Path("data/processed/llm_human_exception_queue.jsonl").exists()
    assert Path("outputs/llm_semantic_merge_judgment_report.md").exists()
    assert Path("outputs/llm_ai_reviewed_cluster_groups_report.md").exists()
    assert Path("outputs/llm_human_exception_queue_report.md").exists()
    assert Path("outputs/llm_semantic_merge_comparison_report.md").exists()
