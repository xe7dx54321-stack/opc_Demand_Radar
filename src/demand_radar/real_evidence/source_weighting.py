"""Stage R1: Source type weighting for pipeline scoring."""
from __future__ import annotations

SOURCE_WEIGHTS: dict[str, float] = {
    "product_review": 0.95,
    "community_discussion": 0.90,
    "github_issue": 0.90,
    "interview_note": 0.90,
    "case_study": 0.75,
    "pricing_page": 0.70,
    "job_posting": 0.70,
    "product_docs": 0.60,
    "landing_page": 0.55,
    "newsletter": 0.55,
    "analyst_article": 0.50,
    "blog_post": 0.45,
    "forum_post": 0.70,
    "social_post": 0.40,
    "marketing_article": 0.25,
    "unknown": 0.30,
}

HIGH_VALUE_SOURCES = {
    "product_review", "community_discussion", "github_issue",
    "case_study", "pricing_page", "interview_note", "job_posting",
}


def get_source_weight(source_type: str) -> float:
    return SOURCE_WEIGHTS.get(source_type, SOURCE_WEIGHTS["unknown"])


def is_high_value_source(source_type: str) -> bool:
    return source_type in HIGH_VALUE_SOURCES
