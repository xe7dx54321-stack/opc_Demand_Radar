"""Tests for evidence_gap_analyzer.py"""
from demand_radar.evidence_gap.evidence_gap_analyzer import analyze_gaps
from demand_radar.state.raw_store import utc_now_iso

BASE_DIMS = {
    "pain_evidence_strength": 70.0,
    "frequency_repetition": 70.0,
    "existing_workaround": 65.0,
    "willingness_to_pay": 60.0,
    "persona_clarity": 75.0,
}

def make_ts(level="medium", action="needs_more_evidence", dims=None, score=62.0, ev=4, src=3):
    return dict(
        truth_score_id="truth_score_000001",
        source_group_id="g1",
        group_title_zh="内容团队选题困难",
        truth_score=score,
        truth_level=level,
        recommended_next_action=action,
        dimension_scores=dims or BASE_DIMS.copy(),
        evidence_count=ev,
        source_count=src,
        personas=["content_team"],
        domain_tags=["content_production"],
        created_at=utc_now_iso(),
    )

def test_medium_candidate_analyzed():
    gaps = analyze_gaps([make_ts("medium")])
    assert len(gaps) == 1
    assert gaps[0].current_truth_level == "medium"

def test_weak_excluded_by_default():
    gaps = analyze_gaps([make_ts("weak")])
    assert len(gaps) == 0

def test_weak_included_when_flag():
    gaps = analyze_gaps([make_ts("weak")], include_weak=True)
    assert len(gaps) == 1

def test_low_wtp_generates_budget_signal():
    dims = dict(BASE_DIMS, willingness_to_pay=30.0)
    gaps = analyze_gaps([make_ts(dims=dims)])
    assert len(gaps) == 1
    missing = gaps[0].missing_evidence_types
    assert any(m in missing for m in ("budget_signal", "paid_alternative", "business_impact"))

def test_low_frequency_generates_frequency_signal():
    dims = dict(BASE_DIMS, frequency_repetition=40.0)
    gaps = analyze_gaps([make_ts(dims=dims)])
    missing = gaps[0].missing_evidence_types
    assert any(m in missing for m in ("frequency_signal", "repeated_workflow", "source_diversity"))

def test_low_persona_generates_persona_signal():
    dims = dict(BASE_DIMS, persona_clarity=30.0)
    gaps = analyze_gaps([make_ts(dims=dims)])
    missing = gaps[0].missing_evidence_types
    assert any(m in missing for m in ("persona_specificity", "target_role_clarity"))

def test_target_signals_increases_with_gaps():
    few_dims = dict(BASE_DIMS, willingness_to_pay=30.0)
    many_dims = dict(BASE_DIMS, willingness_to_pay=30.0, frequency_repetition=30.0,
                     persona_clarity=30.0, existing_workaround=30.0)
    few_gap = analyze_gaps([make_ts(dims=few_dims)])[0]
    many_gap = analyze_gaps([make_ts(dims=many_dims)])[0]
    assert many_gap.target_new_signals >= few_gap.target_new_signals

def test_priority_high_for_close_to_strong():
    gaps = analyze_gaps([make_ts(score=65.0)])
    assert gaps[0].priority == "high"

def test_priority_low_for_low_score():
    gaps = analyze_gaps([make_ts(score=50.0, level="medium")])
    assert gaps[0].priority in ("low", "medium")

def test_gap_reason_zh_nonempty():
    gaps = analyze_gaps([make_ts()])
    assert gaps[0].gap_reason_zh.strip()

def test_insufficient_excluded():
    gaps = analyze_gaps([make_ts("insufficient")])
    assert len(gaps) == 0

def test_strong_included():
    gaps = analyze_gaps([make_ts("strong", action="proceed_to_fit_scoring", score=80.0)])
    assert len(gaps) == 1
