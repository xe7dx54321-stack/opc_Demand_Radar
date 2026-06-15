"""Tests for evidence_gap_schema.py"""
import pytest
from demand_radar.evidence_gap.evidence_gap_schema import (
    EvidenceGapAnalysis, TargetedSignalCollectionPlan,
)
from demand_radar.state.raw_store import utc_now_iso

DIMS = {
    "pain_evidence_strength": 50.0,
    "frequency_repetition": 45.0,
    "existing_workaround": 40.0,
    "willingness_to_pay": 35.0,
    "persona_clarity": 55.0,
}

def make_gap(**kw):
    base = dict(
        gap_analysis_id="evidence_gap_000001",
        truth_score_id="truth_score_000001",
        source_group_id="g1",
        group_title_zh="内容团队选题困难",
        current_truth_score=62.0,
        current_truth_level="medium",
        current_next_action="needs_more_evidence",
        dimension_scores=DIMS.copy(),
        missing_evidence_types=["budget_signal", "frequency_signal"],
        main_bottleneck_dimensions=["willingness_to_pay", "frequency_repetition"],
        gap_reason_zh="付费意愿信号弱。",
        upgrade_path_zh="补充付费证据。",
        target_new_signals=5,
        priority="high",
        created_at=utc_now_iso(),
    )
    base.update(kw)
    return base

def test_valid_gap():
    g = EvidenceGapAnalysis(**make_gap())
    assert g.priority == "high"
    assert len(g.missing_evidence_types) == 2

def test_empty_missing_raises():
    with pytest.raises(Exception):
        EvidenceGapAnalysis(**make_gap(missing_evidence_types=[]))

def test_empty_reason_raises():
    with pytest.raises(Exception):
        EvidenceGapAnalysis(**make_gap(gap_reason_zh=""))

def test_empty_path_raises():
    with pytest.raises(Exception):
        EvidenceGapAnalysis(**make_gap(upgrade_path_zh=""))

def test_invalid_priority_raises():
    with pytest.raises(Exception):
        EvidenceGapAnalysis(**make_gap(priority="critical"))

def test_valid_priorities():
    for pri in ("high", "medium", "low"):
        g = EvidenceGapAnalysis(**make_gap(priority=pri))
        assert g.priority == pri

def make_plan(**kw):
    base = dict(
        plan_id="signal_plan_000001",
        gap_analysis_id="evidence_gap_000001",
        truth_score_id="truth_score_000001",
        source_group_id="g1",
        group_title_zh="内容团队选题",
        target_new_signals=5,
        search_keywords_zh=["内容 选题 痛点"],
        search_keywords_en=["content topic pain"],
        positive_signal_criteria=["具体付费证据"],
        negative_signal_criteria=["没有成本语境"],
        collection_notes_zh="建议采集付费信号。",
        expected_impact_zh="预期提升到 70 分。",
        created_at=utc_now_iso(),
    )
    base.update(kw)
    return base

def test_valid_plan():
    p = TargetedSignalCollectionPlan(**make_plan())
    assert p.target_new_signals == 5

def test_empty_positive_raises():
    with pytest.raises(Exception):
        TargetedSignalCollectionPlan(**make_plan(positive_signal_criteria=[]))

def test_empty_negative_raises():
    with pytest.raises(Exception):
        TargetedSignalCollectionPlan(**make_plan(negative_signal_criteria=[]))

def test_empty_notes_raises():
    with pytest.raises(Exception):
        TargetedSignalCollectionPlan(**make_plan(collection_notes_zh=""))
