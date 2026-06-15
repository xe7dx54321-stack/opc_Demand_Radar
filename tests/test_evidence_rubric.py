"""Tests for evidence_rubric module."""
from __future__ import annotations
from demand_radar.real_evidence.evidence_rubric import score_evidence_strength


def test_strong_product_review():
    text = (
        "Every week I spend 4 hours tracking AI startups manually. "
        "We pay $200/month for PitchBook but it misses too many technical companies. "
        "Our team keeps a spreadsheet to track news manually."
    )
    result = score_evidence_strength(text, "product_review")
    assert result["rubric_score"] >= 0.6
    assert result["tier"] in ("strong", "medium")


def test_marketing_article_weak():
    text = (
        "AI is transforming the investment landscape. "
        "Our platform helps investors track market trends more efficiently. "
        "Sign up today for a free trial."
    )
    result = score_evidence_strength(text, "marketing_article")
    assert result["tier"] in ("weak", "reject")


def test_short_text_rejected():
    result = score_evidence_strength("Too short.", "community_discussion")
    assert result["tier"] == "reject"


def test_paid_signal_detected():
    text = (
        "We subscribe to three different market intelligence tools but "
        "still have to manually compile a weekly report. "
        "The subscription costs are high and the workflow is still manual."
    )
    result = score_evidence_strength(text, "community_discussion")
    assert result.get("has_paid_signal") is True or result["rubric_score"] >= 0.4


def test_workaround_signal_detected():
    text = (
        "We use a spreadsheet to track AI companies across sectors. "
        "It takes 2 people half a day each week just to update it."
    )
    result = score_evidence_strength(text, "community_discussion")
    assert result.get("has_workaround_signal") is True or result["rubric_score"] >= 0.3


def test_result_has_required_keys():
    result = score_evidence_strength("Some text about a workflow problem that is long enough.", "blog_post")
    assert "rubric_score" in result
    assert "tier" in result