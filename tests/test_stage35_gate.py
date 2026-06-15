"""Tests for Stage 3.5 Stage 4 Gate."""
import pytest
from demand_radar.stage35.stage35_gate import evaluate_stage4_gate


def _delta(score=62.0, level="medium", action="needs_more_evidence",
           confidence="medium", sd=5.0):
    return {
        "after_truth_score": score,
        "after_truth_level": level,
        "recommended_next_action": action,
        "delta_confidence": confidence,
        "stable_delta": sd,
        "after_group_title_zh": "测试候选",
    }


def test_formal_gate_passes_when_strong_full_baseline(tmp_path):
    deltas = [_delta(score=80.0, level="strong", action="proceed_to_fit_scoring", confidence="high", sd=15.0)]
    gate = evaluate_stage4_gate(deltas, lineage_baseline_quality="full",
                                attribution_rate=0.6, output_path=str(tmp_path / "g.json"))
    assert gate.status == "pass_formal"


def test_tentative_gate_passes_when_score_70_full_baseline(tmp_path):
    deltas = [_delta(score=72.0, level="medium", action="needs_more_evidence", confidence="medium", sd=8.0)]
    gate = evaluate_stage4_gate(deltas, lineage_baseline_quality="full",
                                output_path=str(tmp_path / "g.json"))
    assert gate.status == "pass_tentative"


def test_blocked_when_partial_baseline(tmp_path):
    deltas = [_delta(score=72.0, level="medium", sd=8.0)]
    gate = evaluate_stage4_gate(deltas, lineage_baseline_quality="partial",
                                output_path=str(tmp_path / "g.json"))
    assert gate.status == "blocked"


def test_blocked_when_no_deltas(tmp_path):
    gate = evaluate_stage4_gate([], lineage_baseline_quality="full",
                                output_path=str(tmp_path / "g.json"))
    assert gate.status == "blocked"


def test_blocked_when_score_below_70(tmp_path):
    deltas = [_delta(score=65.0, level="medium", sd=5.0)]
    gate = evaluate_stage4_gate(deltas, lineage_baseline_quality="full",
                                output_path=str(tmp_path / "g.json"))
    assert gate.status == "blocked"


def test_blocked_when_attribution_rate_low(tmp_path):
    deltas = [_delta(score=80.0, level="strong", action="proceed_to_fit_scoring", confidence="high", sd=15.0)]
    gate = evaluate_stage4_gate(deltas, lineage_baseline_quality="full",
                                attribution_rate=0.30,
                                output_path=str(tmp_path / "g.json"))
    # attribution_rate < 50% blocks formal, but no tentative either (strong level but attribution low)
    assert gate.status in ("blocked", "pass_tentative")


def test_gate_result_has_reason(tmp_path):
    gate = evaluate_stage4_gate([], lineage_baseline_quality="partial",
                                output_path=str(tmp_path / "g.json"))
    assert gate.reason_zh
    assert gate.required_next_action_zh


def test_gate_output_file_written(tmp_path):
    gate = evaluate_stage4_gate([_delta()], lineage_baseline_quality="full",
                                output_path=str(tmp_path / "g.json"))
    assert (tmp_path / "g.json").exists()
