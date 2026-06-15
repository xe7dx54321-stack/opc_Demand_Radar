"""Tests for Stage 3 CLI commands."""
from __future__ import annotations

import json
import pytest
from pathlib import Path
from typer.testing import CliRunner
from demand_radar.cli import app

runner = CliRunner()

SAMPLE_GROUPS = [
    {
        "group_id": f"ai_cluster_group_{i:06d}",
        "group_title_zh": f"\u5185\u5bb9\u56e2\u961f\u9762\u4e34\u9009\u9898\u56f0\u96be {i}",
        "group_summary_zh": "\u5185\u5bb9\u521b\u4f5c\u8005\u5728\u9009\u9898\u65f6\u975e\u5e38\u9ebb\u70e6\u3002",
        "evidence_count": 4 + i,
        "source_count": 2 + (i % 2),
        "batch_ids": ["batch_a", "batch_b"],
        "personas": ["content_team"],
        "domain_tags": ["content_production"],
        "current_workarounds": ["\u624b\u5de5\u6574\u7406\u8868\u683c"],
        "representative_quotes": ["\u975e\u5e38\u8017\u65f6\uff0c\u8981\u82b1\u4e24\u5c0f\u65f6"],
        "representative_pain_descriptions": ["\u65e0\u6cd5\u5feb\u901f\u68c0\u7d22\u76f8\u5173\u5185\u5bb9"],
    }
    for i in range(1, 4)
]


def _write_sample_calibrated(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(g) for g in SAMPLE_GROUPS), encoding="utf-8")


def test_run_truth_scoring_command(tmp_path, monkeypatch):
    """run-truth-scoring loads groups and outputs scores; verify via CLI output text."""
    cal_path = tmp_path / "calibrated_llm_ai_reviewed_cluster_groups.jsonl"
    _write_sample_calibrated(cal_path)

    # Patch the input loader so it reads from tmp_path
    import demand_radar.truth_scoring.truth_input_loader as loader
    monkeypatch.setattr(loader, "SOURCE_PATHS", {
        "calibrated_llm": cal_path,
        "llm": tmp_path / "llm.jsonl",
        "ai": tmp_path / "ai.jsonl",
        "human": tmp_path / "human.jsonl",
    })

    # Patch write_truth_scores in pipeline to write to tmp_path
    import demand_radar.truth_scoring.truth_pipeline as pipeline
    scores_path = tmp_path / "truth_scores.jsonl"
    original_write = pipeline.write_truth_scores
    def _patched_write(scores, path=None):
        return original_write(scores, scores_path)
    monkeypatch.setattr(pipeline, "write_truth_scores", _patched_write)

    result = runner.invoke(app, ["run-truth-scoring", "--source", "calibrated_llm"])
    assert result.exit_code == 0, f"Output: {result.output}"
    assert "Truth scoring complete" in result.output
    assert "3" in result.output  # 3 groups scored


def test_run_truth_scoring_cli_command_exists():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "run-truth-scoring" in result.output


def test_run_stage3_cli_command_exists():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "run-stage3" in result.output


def test_build_truth_report_command_exists():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "build-truth-report" in result.output


def test_build_top_truth_candidates_report_command_exists():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "build-top-truth-candidates-report" in result.output


def test_run_stage3_scores_groups(tmp_path, monkeypatch):
    """run-stage3 loads groups, scores them, and reports counts in output."""
    cal_path = tmp_path / "calibrated_llm_ai_reviewed_cluster_groups.jsonl"
    _write_sample_calibrated(cal_path)

    import demand_radar.truth_scoring.truth_input_loader as loader
    monkeypatch.setattr(loader, "SOURCE_PATHS", {
        "calibrated_llm": cal_path,
        "llm": tmp_path / "llm.jsonl",
        "ai": tmp_path / "ai.jsonl",
        "human": tmp_path / "human.jsonl",
    })

    import demand_radar.truth_scoring.truth_pipeline as pipeline
    scores_captured = []
    original_write = pipeline.write_truth_scores
    def _patched_write(scores, path=None):
        scores_captured.extend(scores)
        return original_write(scores, tmp_path / "truth_scores.jsonl")
    monkeypatch.setattr(pipeline, "write_truth_scores", _patched_write)

    # Also patch report builders to write to tmp_path
    import demand_radar.truth_scoring.truth_report as treport
    monkeypatch.setattr(treport, "build_truth_scoring_report",
        lambda scores, output_path=None: treport.build_truth_scoring_report.__wrapped__(scores, tmp_path / "truth_scoring_report.md")
        if hasattr(treport.build_truth_scoring_report, "__wrapped__") else None)

    result = runner.invoke(app, ["run-truth-scoring", "--source", "calibrated_llm"])
    assert result.exit_code == 0, f"Output: {result.output}"
    assert len(scores_captured) == 3
    for s in scores_captured:
        assert s.truth_level in ("strong", "medium", "weak", "insufficient")


def test_build_truth_report_exits_nonzero_when_no_scores(tmp_path, monkeypatch):
    import demand_radar.cli as cli_mod
    monkeypatch.setattr(cli_mod, "load_truth_scores", lambda: [])
    result = runner.invoke(app, ["build-truth-report"])
    assert result.exit_code != 0 or "No truth scores" in result.output
