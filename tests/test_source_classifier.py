"""Tests for source_classifier module."""
from __future__ import annotations
from demand_radar.real_evidence.source_classifier import (
    classify_source_quality,
    classify_signal_types,
)


def test_product_review_quality():
    assert classify_source_quality("product_review") == "high"


def test_community_discussion_quality():
    assert classify_source_quality("community_discussion") == "high"


def test_github_issue_quality():
    assert classify_source_quality("github_issue") == "high"


def test_interview_note_quality():
    assert classify_source_quality("interview_note") == "high"


def test_landing_page_quality():
    assert classify_source_quality("landing_page") == "medium"


def test_social_post_quality():
    q = classify_source_quality("social_post")
    assert q in ("low", "medium")


def test_marketing_article_quality():
    q = classify_source_quality("marketing_article")
    assert q == "low"


def test_unknown_source_quality():
    q = classify_source_quality("totally_unknown_type")
    assert q in ("low", "unknown", "medium")


def test_product_review_signals_pain():
    signals = classify_signal_types("product_review")
    assert "pain_signal" in signals


def test_pricing_page_signals_paid():
    """pricing_page should signal paid_signal, not pain_signal."""
    signals = classify_signal_types("pricing_page")
    assert "paid_signal" in signals


def test_case_study_signals_business_impact():
    signals = classify_signal_types("case_study")
    assert "business_impact_signal" in signals


def test_job_posting_signals():
    signals = classify_signal_types("job_posting")
    assert len(signals) >= 1