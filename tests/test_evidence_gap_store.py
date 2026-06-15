"""Tests for evidence_gap_store.py"""
from demand_radar.evidence_gap.evidence_gap_schema import EvidenceGapAnalysis, TargetedSignalCollectionPlan
from demand_radar.evidence_gap.evidence_gap_store import (
    write_gap_analysis, load_gap_analysis,
    write_collection_plans, load_collection_plans,
)
from demand_radar.state.raw_store import utc_now_iso

DIMS = {"pain_evidence_strength": 55.0, "frequency_repetition": 45.0,
        "existing_workaround": 40.0, "willingness_to_pay": 30.0, "persona_clarity": 55.0}

def make_gap(gid="evidence_gap_000001"):
    return EvidenceGapAnalysis(
        gap_analysis_id=gid, truth_score_id="ts1", source_group_id="g1",
        group_title_zh="测试需求组",
        current_truth_score=62.0, current_truth_level="medium",
        current_next_action="needs_more_evidence", dimension_scores=DIMS.copy(),
        missing_evidence_types=["budget_signal"],
        main_bottleneck_dimensions=["willingness_to_pay"],
        gap_reason_zh="付费信号弱。",
        upgrade_path_zh="补充付费证据。",
        target_new_signals=5, priority="high", created_at=utc_now_iso(),
    )

def make_plan():
    return TargetedSignalCollectionPlan(
        plan_id="signal_plan_000001", gap_analysis_id="evidence_gap_000001",
        truth_score_id="ts1", source_group_id="g1", group_title_zh="测试",
        target_new_signals=5, search_keywords_zh=["测试 关键词"],
        search_keywords_en=["test keyword"],
        positive_signal_criteria=["正向标准"],
        negative_signal_criteria=["负向标准"],
        collection_notes_zh="采集建议。",
        expected_impact_zh="预期提升。",
        created_at=utc_now_iso(),
    )

def test_write_and_load_gaps(tmp_path):
    path = tmp_path / "gaps.jsonl"
    gaps = [make_gap("evidence_gap_000001"), make_gap("evidence_gap_000002")]
    n = write_gap_analysis(gaps, path)
    assert n == 2
    loaded = load_gap_analysis(path)
    assert len(loaded) == 2
    assert loaded[0].gap_analysis_id == "evidence_gap_000001"

def test_load_missing_gaps(tmp_path):
    assert load_gap_analysis(tmp_path / "missing.jsonl") == []

def test_write_and_load_plans(tmp_path):
    path = tmp_path / "plans.jsonl"
    plans = [make_plan()]
    n = write_collection_plans(plans, path)
    assert n == 1
    loaded = load_collection_plans(path)
    assert len(loaded) == 1
    assert loaded[0].plan_id == "signal_plan_000001"

def test_load_missing_plans(tmp_path):
    assert load_collection_plans(tmp_path / "missing.jsonl") == []

def test_overwrite_on_rerun(tmp_path):
    path = tmp_path / "gaps.jsonl"
    write_gap_analysis([make_gap("evidence_gap_000001")], path)
    write_gap_analysis([make_gap("evidence_gap_000002")], path)
    loaded = load_gap_analysis(path)
    assert len(loaded) == 1
    assert loaded[0].gap_analysis_id == "evidence_gap_000002"
