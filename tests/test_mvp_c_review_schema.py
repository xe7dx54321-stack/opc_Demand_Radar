"""Tests for PainSignalReview schema."""
import pytest
from demand_radar.mvp_c.review_schema import PainSignalReview, PainSignalReviewSummary


def _base(**kw):
    d = dict(
        review_id="rev_001",
        pain_item_id="pain__000022",
        candidate_id="cand_abc",
        created_at="2026-01-01T00:00:00Z",
    )
    d.update(kw)
    return d


def test_minimal_valid():
    r = PainSignalReview(**_base())
    assert r.review_id == "rev_001"
    assert r.true_pain is None
    assert r.action_decision is None
    assert r.error_labels == []


def test_full_valid():
    r = PainSignalReview(**_base(
        true_pain=True,
        commercial_potential="high",
        extraction_quality="good",
        domain_relevance_quality="good",
        evidence_quality="strong",
        action_decision="pursue",
        error_labels=[],
        reviewer_note_zh="Very strong signal",
    ))
    assert r.true_pain is True
    assert r.action_decision == "pursue"


def test_invalid_action_decision():
    with pytest.raises(Exception):
        PainSignalReview(**_base(action_decision="invalid_value"))


def test_invalid_commercial_potential():
    with pytest.raises(Exception):
        PainSignalReview(**_base(commercial_potential="very_high"))


def test_invalid_extraction_quality():
    with pytest.raises(Exception):
        PainSignalReview(**_base(extraction_quality="excellent"))


def test_invalid_error_labels():
    with pytest.raises(Exception):
        PainSignalReview(**_base(error_labels=["invented_label"]))


def test_valid_error_labels():
    r = PainSignalReview(**_base(
        error_labels=["bad_persona", "bad_quote", "too_generic"]
    ))
    assert "bad_persona" in r.error_labels


def test_summary_default_zeros():
    s = PainSignalReviewSummary(total_pain_items=5, reviewed_count=0, unreviewed_count=5)
    assert s.true_pain_count == 0
    assert s.pursue_count == 0
    assert s.top_error_labels == {}
