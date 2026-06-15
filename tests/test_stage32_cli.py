"""Tests for Stage 3.2 CLI commands."""
import json
import pytest
from typer.testing import CliRunner
from demand_radar.cli import app
from demand_radar.state.raw_store import utc_now_iso

runner = CliRunner()

DIMS = {
    "pain_evidence_strength": 55.0,
    "frequency_repetition": 45.0,
    "existing_workaround": 40.0,
    "willingness_to_pay": 30.0,
    "persona_clarity": 55.0,
}

def _fake_scores(n=3):
    return [
        {
            "truth_score_id": f"truth_score_{i:06d}",
            "source_type": "calibrated_llm_ai_reviewed_group",
            "source_group_id": f"g{i}",
            "group_title_zh": f"内容团队选题困难 {i}",
            "group_summary_zh": "摘要",
            "truth_score": 62.0,
            "truth_level": "medium",
            "dimension_scores": DIMS,
            "evidence_count": 4,
            "source_count": 3,
            "positive_signals": [],
            "negative_signals": [],
            "risk_flags": [],
            "scoring_reason_zh": "中等证据。",
            "recommended_next_action": "needs_more_evidence",
            "created_at": utc_now_iso(),
        }
        for i in range(1, n + 1)
    ]


def test_analyze_evidence_gaps_command_exists():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "analyze-evidence-gaps" in result.output


def test_run_stage32_command_exists():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "run-stage32" in result.output


def test_build_evidence_gap_report_command_exists():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "build-evidence-gap-report" in result.output


def test_build_targeted_signal_plan_command_exists():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "build-targeted-signal-plan" in result.output


def test_analyze_evidence_gaps_with_scores(tmp_path, monkeypatch):
    scores_path = tmp_path / "truth_scores.jsonl"
    gap_path = tmp_path / "gaps.jsonl"
    plan_path = tmp_path / "plans.jsonl"
    scores_path.write_text(
        "\n".join(json.dumps(s) for s in _fake_scores(3)), encoding="utf-8"
    )
    import demand_radar.truth_scoring.truth_store as ts_store
    import demand_radar.evidence_gap.evidence_gap_store as eg_store
    from demand_radar.evidence_gap.evidence_gap_schema import EvidenceGapAnalysis, TargetedSignalCollectionPlan

    monkeypatch.setattr(ts_store, "TRUTH_SCORES_PATH", scores_path)

    # Patch write functions in cli module to write to tmp paths
    captured_gaps = []
    captured_plans = []
    import demand_radar.cli as cli_mod

    def _fake_write_gaps(gaps, path=None):
        captured_gaps.extend(gaps)
        return eg_store.write_gap_analysis(gaps, gap_path)

    def _fake_write_plans(plans, path=None):
        captured_plans.extend(plans)
        return eg_store.write_collection_plans(plans, plan_path)

    monkeypatch.setattr(cli_mod, "write_gap_analysis", _fake_write_gaps)
    monkeypatch.setattr(cli_mod, "write_collection_plans", _fake_write_plans)

    result = runner.invoke(app, ["analyze-evidence-gaps"])
    assert result.exit_code == 0, f"Output: {result.output}"
    assert "Evidence gap analysis complete" in result.output
    assert len(captured_gaps) > 0
    assert len(captured_plans) > 0


def test_analyze_evidence_gaps_fails_without_scores(monkeypatch):
    import demand_radar.cli as cli_mod
    monkeypatch.setattr(cli_mod, "load_truth_scores", lambda: [])
    result = runner.invoke(app, ["analyze-evidence-gaps"])
    assert result.exit_code != 0 or "No truth scores" in result.output
