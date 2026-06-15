"""Tests for truth_gate.py"""
from demand_radar.truth_scoring.truth_gate import apply_truth_gate, compute_truth_level

GOOD_DIMS = {
    "pain_evidence_strength": 80.0,
    "frequency_repetition": 75.0,
    "existing_workaround": 70.0,
    "willingness_to_pay": 65.0,
    "persona_clarity": 85.0,
}


def test_compute_level_strong():
    assert compute_truth_level(80.0) == "strong"


def test_compute_level_medium():
    assert compute_truth_level(60.0) == "medium"


def test_compute_level_weak():
    assert compute_truth_level(45.0) == "weak"


def test_compute_level_insufficient():
    assert compute_truth_level(20.0) == "insufficient"


def test_evidence_gate_caps_at_weak():
    flags = []
    level, action = apply_truth_gate(80.0, "strong", evidence_count=1, source_count=3, dimension_scores=GOOD_DIMS, risk_flags=flags)
    assert level == "weak"
    assert action in ("keep_watch", "needs_more_evidence", "discard")


def test_single_source_gate_adds_flag():
    flags = []
    level, action = apply_truth_gate(80.0, "strong", evidence_count=5, source_count=1, dimension_scores=GOOD_DIMS, risk_flags=flags)
    assert "single_source_risk" in flags
    assert level in ("medium", "weak", "insufficient")


def test_low_persona_caps_at_medium():
    dims = dict(GOOD_DIMS, persona_clarity=30.0)
    flags = []
    level, action = apply_truth_gate(80.0, "strong", evidence_count=5, source_count=3, dimension_scores=dims, risk_flags=flags)
    assert "unclear_persona" in flags
    assert level in ("medium", "weak", "insufficient")


def test_low_pain_evidence_caps_at_weak():
    dims = dict(GOOD_DIMS, pain_evidence_strength=30.0)
    flags = []
    level, action = apply_truth_gate(80.0, "strong", evidence_count=5, source_count=3, dimension_scores=dims, risk_flags=flags)
    assert "weak_pain_evidence" in flags
    assert level == "weak"


def test_proceed_action_for_strong_no_risk():
    flags = []
    level, action = apply_truth_gate(80.0, "strong", evidence_count=5, source_count=3, dimension_scores=GOOD_DIMS, risk_flags=flags)
    assert level == "strong"
    assert action == "proceed_to_fit_scoring"


def test_medium_gives_needs_more_evidence():
    flags = []
    level, action = apply_truth_gate(60.0, "medium", evidence_count=3, source_count=2, dimension_scores=GOOD_DIMS, risk_flags=flags)
    assert level == "medium"
    assert action == "needs_more_evidence"


def test_insufficient_gives_discard():
    dims = dict(GOOD_DIMS, pain_evidence_strength=20.0)
    flags = []
    level, action = apply_truth_gate(20.0, "insufficient", evidence_count=1, source_count=1, dimension_scores=dims, risk_flags=flags)
    assert action == "discard"


def test_no_flags_when_all_good():
    flags = []
    apply_truth_gate(80.0, "strong", evidence_count=5, source_count=3, dimension_scores=GOOD_DIMS, risk_flags=flags)
    assert flags == []
