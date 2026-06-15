"""Stage R1: Source type classifier."""
from __future__ import annotations

# Ordered by credibility for pain evidence
_PAIN_CREDIBILITY = {
    "product_review": "high",
    "community_discussion": "high",
    "github_issue": "high",
    "interview_note": "high",
    "case_study": "medium",
    "forum_post": "medium",
    "job_posting": "medium",
    "pricing_page": "medium",
    "product_docs": "medium",
    "analyst_article": "medium",
    "landing_page": "medium",
    "newsletter": "low",
    "blog_post": "low",
    "social_post": "low",
    "marketing_article": "low",
    "unknown": "low",
}

_PAID_SIGNAL_SOURCES = {"pricing_page", "product_review", "case_study", "landing_page"}
_PAIN_SIGNAL_SOURCES = {"product_review", "community_discussion", "github_issue", "interview_note", "forum_post"}
_IMPACT_SIGNAL_SOURCES = {"case_study", "job_posting", "analyst_article"}
_WORKAROUND_SIGNAL_SOURCES = {"community_discussion", "github_issue", "interview_note", "forum_post", "product_review"}


def classify_source_quality(source_type: str) -> str:
    return _PAIN_CREDIBILITY.get(source_type, "low")


def classify_signal_types(source_type: str) -> list[str]:
    """Return which signal types this source can credibly provide."""
    signals: list[str] = []
    if source_type in _PAIN_SIGNAL_SOURCES:
        signals.append("pain_signal")
    if source_type in _PAID_SIGNAL_SOURCES:
        signals.append("paid_signal")
    if source_type in _IMPACT_SIGNAL_SOURCES:
        signals.append("business_impact_signal")
    if source_type in _WORKAROUND_SIGNAL_SOURCES:
        signals.append("workaround_signal")
    return signals
