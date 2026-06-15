"""Tests for signal_collection_plan.py"""
from demand_radar.evidence_gap.evidence_gap_schema import EvidenceGapAnalysis
from demand_radar.evidence_gap.signal_collection_plan import build_collection_plans
from demand_radar.state.raw_store import utc_now_iso

DIMS = {
    "pain_evidence_strength": 55.0,
    "frequency_repetition": 45.0,
    "existing_workaround": 40.0,
    "willingness_to_pay": 30.0,
    "persona_clarity": 55.0,
}

def make_gap(title="内容团队选题", missing=None):
    return EvidenceGapAnalysis(
        gap_analysis_id="evidence_gap_000001",
        truth_score_id="truth_score_000001",
        source_group_id="g1",
        group_title_zh=title,
        current_truth_score=62.0,
        current_truth_level="medium",
        current_next_action="needs_more_evidence",
        dimension_scores=DIMS.copy(),
        missing_evidence_types=missing or ["budget_signal", "frequency_signal"],
        main_bottleneck_dimensions=["willingness_to_pay", "frequency_repetition"],
        gap_reason_zh="付费意愿弱。",
        upgrade_path_zh="补充付费证据。",
        target_new_signals=5,
        priority="high",
        created_at=utc_now_iso(),
    )

def test_builds_plan_for_each_gap():
    gaps = [make_gap(), make_gap("运营知识库")]
    plans = build_collection_plans(gaps)
    assert len(plans) == 2

def test_plan_has_keywords():
    plans = build_collection_plans([make_gap()])
    p = plans[0]
    assert p.search_keywords_zh or p.search_keywords_en

def test_plan_has_positive_criteria():
    plans = build_collection_plans([make_gap()])
    assert plans[0].positive_signal_criteria

def test_plan_has_negative_criteria():
    plans = build_collection_plans([make_gap()])
    assert plans[0].negative_signal_criteria

def test_budget_missing_gives_pricing_sources():
    plans = build_collection_plans([make_gap(missing=["budget_signal"])])
    assert any("pricing" in s or "review" in s or "case" in s for s in plans[0].target_source_types)

def test_persona_missing_gives_job_posting():
    plans = build_collection_plans([make_gap(missing=["persona_specificity"])])
    assert any("job" in s or "interview" in s for s in plans[0].target_source_types)

def test_content_domain_detected():
    plans = build_collection_plans([make_gap("内容团队选题困难")])
    assert any("内容" in kw or "content" in kw for kw in plans[0].search_keywords_zh + plans[0].search_keywords_en)

def test_plan_target_signals_matches_gap():
    gap = make_gap()
    plans = build_collection_plans([gap])
    assert plans[0].target_new_signals == gap.target_new_signals
