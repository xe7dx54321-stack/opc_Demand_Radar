"""Tests for truth_store.py"""
import pytest
from demand_radar.truth_scoring.truth_store import (
    write_truth_scores,
    load_truth_scores,
    append_truth_score_review,
    load_truth_score_reviews,
    get_latest_review,
)
from demand_radar.truth_scoring.truth_schema import TruthScore, TruthScoreReview
from demand_radar.state.raw_store import utc_now_iso

DIMS = {
    "pain_evidence_strength": 60.0,
    "frequency_repetition": 50.0,
    "existing_workaround": 40.0,
    "willingness_to_pay": 30.0,
    "persona_clarity": 80.0,
}


def make_score(score_id="truth_score_000001", level="medium"):
    return TruthScore(
        truth_score_id=score_id,
        source_type="calibrated_llm_ai_reviewed_group",
        source_group_id="g1",
        group_title_zh="\u9700\u6c42\u7ec4A",
        group_summary_zh="\u6458\u8981A",
        truth_score=60.0,
        truth_level=level,
        dimension_scores=DIMS.copy(),
        evidence_count=3,
        source_count=2,
        scoring_reason_zh="\u75db\u70b9\u4e2d\u7b49\u3002",
        recommended_next_action="needs_more_evidence",
        created_at=utc_now_iso(),
    )


def test_write_and_load(tmp_path):
    path = tmp_path / "scores.jsonl"
    scores = [make_score("truth_score_000001"), make_score("truth_score_000002")]
    count = write_truth_scores(scores, path)
    assert count == 2
    loaded = load_truth_scores(path)
    assert len(loaded) == 2
    assert loaded[0].truth_score_id == "truth_score_000001"


def test_load_missing_file(tmp_path):
    path = tmp_path / "missing.jsonl"
    result = load_truth_scores(path)
    assert result == []


def test_append_review(tmp_path):
    path = tmp_path / "reviews.jsonl"
    review = TruthScoreReview(
        review_id="truth_score_review_000001",
        truth_score_id="truth_score_000001",
        source_group_id="g1",
        label="score_reasonable",
        created_at=utc_now_iso(),
    )
    append_truth_score_review(review, path)
    loaded = load_truth_score_reviews(path)
    assert len(loaded) == 1
    assert loaded[0].label == "score_reasonable"


def test_append_multiple_reviews(tmp_path):
    path = tmp_path / "reviews.jsonl"
    for i, label in enumerate(["score_reasonable", "score_too_high", "bad_evidence"]):
        review = TruthScoreReview(
            review_id=f"truth_score_review_{i:06d}",
            truth_score_id="truth_score_000001",
            source_group_id="g1",
            label=label,
            created_at=utc_now_iso(),
        )
        append_truth_score_review(review, path)
    reviews = load_truth_score_reviews(path)
    assert len(reviews) == 3


def test_get_latest_review(tmp_path):
    path = tmp_path / "reviews.jsonl"
    for i, label in enumerate(["score_reasonable", "score_too_high"]):
        review = TruthScoreReview(
            review_id=f"truth_score_review_{i:06d}",
            truth_score_id="truth_score_000001",
            source_group_id="g1",
            label=label,
            created_at=utc_now_iso(),
        )
        append_truth_score_review(review, path)
    latest = get_latest_review("truth_score_000001", path)
    assert latest is not None
    assert latest.label == "score_too_high"


def test_get_latest_review_not_found(tmp_path):
    path = tmp_path / "reviews.jsonl"
    result = get_latest_review("nonexistent_id", path)
    assert result is None


def test_write_empty_list(tmp_path):
    path = tmp_path / "scores.jsonl"
    write_truth_scores([], path)
    loaded = load_truth_scores(path)
    assert loaded == []
