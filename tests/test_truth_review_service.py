"""Tests for truth_review_service.py"""
import pytest
from demand_radar.ui.truth_review_service import get_truth_scores, submit_truth_review
from demand_radar.truth_scoring.truth_schema import TruthScore
from demand_radar.truth_scoring.truth_store import write_truth_scores
from demand_radar.state.raw_store import utc_now_iso

DIMS = {
    "pain_evidence_strength": 60.0,
    "frequency_repetition": 50.0,
    "existing_workaround": 40.0,
    "willingness_to_pay": 30.0,
    "persona_clarity": 80.0,
}


def make_score(score_id="truth_score_000001"):
    return TruthScore(
        truth_score_id=score_id,
        source_type="calibrated_llm_ai_reviewed_group",
        source_group_id="g1",
        group_title_zh="\u9700\u6c42\u7ec4",
        group_summary_zh="\u6458\u8981",
        truth_score=60.0,
        truth_level="medium",
        dimension_scores=DIMS.copy(),
        evidence_count=3,
        source_count=2,
        scoring_reason_zh="\u4e2d\u7b49\u8bc1\u636e\u3002",
        recommended_next_action="needs_more_evidence",
        created_at=utc_now_iso(),
    )


def test_get_truth_scores_empty(tmp_path, monkeypatch):
    import demand_radar.truth_scoring.truth_store as store
    monkeypatch.setattr(store, "TRUTH_SCORES_PATH", tmp_path / "missing.jsonl")
    import demand_radar.ui.truth_review_service as svc
    monkeypatch.setattr(svc, "load_truth_scores", lambda path=None: [])
    scores = get_truth_scores()
    assert scores == []


def test_submit_truth_review_creates_record(tmp_path, monkeypatch):
    import demand_radar.truth_scoring.truth_store as store
    monkeypatch.setattr(store, "TRUTH_REVIEWS_PATH", tmp_path / "reviews.jsonl")
    review = submit_truth_review(
        truth_score_id="truth_score_000001",
        source_group_id="g1",
        label="score_reasonable",
    )
    assert review.label == "score_reasonable"
    assert review.review_id.startswith("truth_score_review_")


def test_submit_invalid_label_raises(tmp_path, monkeypatch):
    import demand_radar.truth_scoring.truth_store as store
    monkeypatch.setattr(store, "TRUTH_REVIEWS_PATH", tmp_path / "reviews.jsonl")
    with pytest.raises(Exception):
        submit_truth_review("ts1", "g1", "invalid_label")
