"""Tests for evidence_gap_report.py"""
from demand_radar.evidence_gap.evidence_gap_schema import EvidenceGapAnalysis, TargetedSignalCollectionPlan
from demand_radar.evidence_gap.evidence_gap_report import build_evidence_gap_report, build_targeted_signal_plan_report
from demand_radar.state.raw_store import utc_now_iso

DIMS = {"pain_evidence_strength": 55.0, "frequency_repetition": 45.0,
        "existing_workaround": 40.0, "willingness_to_pay": 30.0, "persona_clarity": 55.0}

def make_gap(gid="g1", pri="high"):
    return EvidenceGapAnalysis(
        gap_analysis_id=gid, truth_score_id="ts1", source_group_id="sg1",
        group_title_zh="内容选题困难",
        current_truth_score=62.0, current_truth_level="medium",
        current_next_action="needs_more_evidence", dimension_scores=DIMS.copy(),
        missing_evidence_types=["budget_signal", "frequency_signal"],
        main_bottleneck_dimensions=["willingness_to_pay"],
        gap_reason_zh="付费信号弱。",
        upgrade_path_zh="补充付费证据。",
        target_new_signals=5, priority=pri, created_at=utc_now_iso(),
    )

def make_plan():
    return TargetedSignalCollectionPlan(
        plan_id="sp1", gap_analysis_id="g1", truth_score_id="ts1", source_group_id="sg1",
        group_title_zh="内容选题困难",
        target_new_signals=5, search_keywords_zh=["内容 选题"],
        search_keywords_en=["content topic"],
        positive_signal_criteria=["有付费证据"],
        negative_signal_criteria=["没有成本语境"],
        collection_notes_zh="采集建议。",
        expected_impact_zh="预期提升。",
        created_at=utc_now_iso(),
    )

def test_evidence_gap_report_created(tmp_path):
    out = tmp_path / "report.md"
    build_evidence_gap_report([make_gap()], out)
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "Evidence Gap Report" in content
    assert "内容选题困难" in content

def test_report_has_summary(tmp_path):
    out = tmp_path / "report.md"
    build_evidence_gap_report([make_gap("g1","high"), make_gap("g2","medium")], out)
    content = out.read_text(encoding="utf-8")
    assert "High priority gaps:" in content
    assert "Truth candidates analyzed: 2" in content

def test_signal_plan_report_created(tmp_path):
    out = tmp_path / "plan.md"
    build_targeted_signal_plan_report([make_plan()], out)
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "Targeted Signal Collection Plan" in content
    assert "Search Keywords" in content

def test_signal_plan_has_total_signals(tmp_path):
    out = tmp_path / "plan.md"
    build_targeted_signal_plan_report([make_plan(), make_plan()], out)
    content = out.read_text(encoding="utf-8")
    assert "Total target new signals: 10" in content
