"""Tests for truth_schema.py"""
import pytest
from demand_radar.truth_scoring.truth_schema import (
    TruthScore,
    TruthScoreReview,
    VALID_TRUTH_LEVELS,
    VALID_NEXT_ACTIONS,
    VALID_REVIEW_LABELS,
)
from demand_radar.state.raw_store import utc_now_iso

VALID_DIMS = {
    "pain_evidence_strength": 60.0,
    "frequency_repetition": 50.0,
    "existing_workaround": 40.0,
    "willingness_to_pay": 30.0,
    "persona_clarity": 80.0,
}


def make_score(**kwargs) -> dict:
    base = dict(
        truth_score_id="truth_score_000001",
        source_type="calibrated_llm_ai_reviewed_group",
        source_group_id="group_001",
        group_title_zh="需求组标题",
        group_summary_zh="需求组摘要",
        truth_score=65.0,
        truth_level="medium",
        dimension_scores=VALID_DIMS.copy(),
        evidence_count=3,
        source_count=2,
        personas=["developer"],
        domain_tags=["saas"],
        positive_signals=["具有明确痛点"],
        negative_signals=[],
        risk_flags=[],
        scoring_reason_zh="痛点证据中等。",
        recommended_next_action="needs_more_evidence",
        created_at=utc_now_iso(),
    )
    base.update(kwargs)
    return base


def test_valid_truth_score():
    s = TruthScore(**make_score())
    assert s.truth_level == "medium"
    assert s.truth_score == 65.0


def test_truth_score_out_of_range():
    with pytest.raises(Exception):
        TruthScore(**make_score(truth_score=150.0))


def test_truth_score_negative():
    with pytest.raises(Exception):
        TruthScore(**make_score(truth_score=-1.0))


def test_invalid_truth_level():
    with pytest.raises(Exception):
        TruthScore(**make_score(truth_level="excellent"))


def test_invalid_next_action():
    with pytest.raises(Exception):
        TruthScore(**make_score(recommended_next_action="buy_now"))


def test_missing_dimension():
    dims = VALID_DIMS.copy()
    del dims["persona_clarity"]
    with pytest.raises(Exception):
        TruthScore(**make_score(dimension_scores=dims))


def test_empty_scoring_reason():
    with pytest.raises(Exception):
        TruthScore(**make_score(scoring_reason_zh=""))


def test_valid_review():
    r = TruthScoreReview(
        review_id="truth_score_review_000001",
        truth_score_id="truth_score_000001",
        source_group_id="group_001",
        label="score_reasonable",
        created_at=utc_now_iso(),
    )
    assert r.label == "score_reasonable"


def test_invalid_review_label():
    with pytest.raises(Exception):
        TruthScoreReview(
            review_id="r1",
            truth_score_id="ts1",
            source_group_id="g1",
            label="bad_label",
            created_at=utc_now_iso(),
        )


def test_review_corrected_level_invalid():
    with pytest.raises(Exception):
        TruthScoreReview(
            review_id="r1",
            truth_score_id="ts1",
            source_group_id="g1",
            label="score_reasonable",
            corrected_truth_level="excellent",
            created_at=utc_now_iso(),
        )


def test_all_truth_levels_valid():
    for level in VALID_TRUTH_LEVELS:
        s = TruthScore(**make_score(truth_level=level, recommended_next_action="keep_watch"))
        assert s.truth_level == level
