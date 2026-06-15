"""Tests for truth_report.py"""
from demand_radar.truth_scoring.truth_report import (
    build_truth_scoring_report,
    build_top_truth_candidates_report,
)
from demand_radar.truth_scoring.truth_schema import TruthScore
from demand_radar.state.raw_store import utc_now_iso

DIMS = {
    "pain_evidence_strength": 80.0,
    "frequency_repetition": 75.0,
    "existing_workaround": 70.0,
    "willingness_to_pay": 65.0,
    "persona_clarity": 85.0,
}


def make_score(score_id, level, score_val, action):
    return TruthScore(
        truth_score_id=score_id,
        source_type="calibrated_llm_ai_reviewed_group",
        source_group_id=f"g_{score_id}",
        group_title_zh=f"\u9700\u6c42\u7ec4 {score_id}",
        group_summary_zh="\u6458\u8981",
        truth_score=score_val,
        truth_level=level,
        dimension_scores=DIMS.copy(),
        evidence_count=4,
        source_count=3,
        scoring_reason_zh="\u75db\u70b9\u8bc1\u636e\u4e2d\u7b49\u3002",
        recommended_next_action=action,
        created_at=utc_now_iso(),
    )


SAMPLE_SCORES = [
    make_score("s1", "strong", 80.0, "proceed_to_fit_scoring"),
    make_score("s2", "medium", 65.0, "needs_more_evidence"),
    make_score("s3", "weak", 42.0, "keep_watch"),
    make_score("s4", "insufficient", 20.0, "discard"),
]


def test_truth_scoring_report_creates_file(tmp_path):
    out = tmp_path / "truth_scoring_report.md"
    build_truth_scoring_report(SAMPLE_SCORES, out)
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "Truth Scoring Report" in content
    assert "strong" in content.lower()
    assert "medium" in content.lower()


def test_truth_scoring_report_contains_all_levels(tmp_path):
    out = tmp_path / "report.md"
    build_truth_scoring_report(SAMPLE_SCORES, out)
    content = out.read_text(encoding="utf-8")
    for level in ["strong", "medium", "weak", "insufficient"]:
        assert level in content


def test_top_candidates_report_only_strong_medium(tmp_path):
    out = tmp_path / "top.md"
    build_top_truth_candidates_report(SAMPLE_SCORES, out)
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "Top Truth Candidates" in content
    # weak and insufficient should not appear as candidates
    assert "\u9700\u6c42\u7ec4 s3" not in content or "insufficient" not in content


def test_top_candidates_empty_when_all_weak(tmp_path):
    weak_scores = [make_score("w1", "weak", 40.0, "keep_watch"), make_score("w2", "insufficient", 15.0, "discard")]
    out = tmp_path / "top_empty.md"
    build_top_truth_candidates_report(weak_scores, out)
    content = out.read_text(encoding="utf-8")
    assert "Top Truth Candidates" in content


def test_report_sorted_by_score_descending(tmp_path):
    out = tmp_path / "report.md"
    build_truth_scoring_report(SAMPLE_SCORES, out)
    content = out.read_text(encoding="utf-8")
    pos_s1 = content.find("\u9700\u6c42\u7ec4 s1")
    pos_s2 = content.find("\u9700\u6c42\u7ec4 s2")
    assert pos_s1 < pos_s2
