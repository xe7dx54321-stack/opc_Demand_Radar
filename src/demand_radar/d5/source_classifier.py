"""Source category and weight rules for D5 evidence consolidation."""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

SOURCE_WEIGHTS = {
    "first_hand_community": 1.0,
    "workaround_discussion": 0.9,
    "product_review_comment": 0.85,
    "practitioner_blog": 0.65,
    "content_marketing": 0.45,
    "vendor_blog": 0.4,
    "job_description": 0.35,
    "generic_article": 0.25,
    "technical_issue": 0.2,
    "unknown": 0.25,
}

COMMUNITY_DOMAINS = (
    "reddit.com",
    "news.ycombinator.com",
    "ycombinator.com",
    "quora.com",
    "stackexchange.com",
    "stackoverflow.com",
)
VENDOR_HINTS = (
    "datatobrief.com",
    "marvin-labs.com",
    "allvuesystems.com",
    "carta.com",
    "conceptor.ai",
    "n8n.io",
)
JOB_HINTS = ("careers", "/career", "/jobs", "/job", "greenhouse", "lever.co", "workable")
REVIEW_HINTS = ("review", "reviews", "comments", "producthunt", "g2.com", "capterra")
WORKAROUND_TERMS = (
    "spreadsheet",
    "google sheets",
    "airtable",
    "notion",
    "manual workflow",
    "manual",
    "what do you use",
    "workaround",
)


def classify_source(row: dict[str, Any]) -> tuple[str, float]:
    """Classify a source into demand-evidence usefulness categories."""
    source_url = str(row.get("source_url") or "")
    domain = str(row.get("result_domain") or urlparse(source_url).netloc or "").lower()
    text = " ".join(
        str(row.get(key) or "")
        for key in (
            "title",
            "source_url",
            "source_type",
            "pain_description_zh",
            "evidence_quote",
            "current_solution",
            "job_to_be_done",
            "commercial_signal_type",
        )
    ).lower()

    if "github" in domain or "github" in text and "issue" in text:
        return "technical_issue", SOURCE_WEIGHTS["technical_issue"]
    if any(term in source_url.lower() or term in text for term in JOB_HINTS):
        return "job_description", SOURCE_WEIGHTS["job_description"]
    if any(domain.endswith(hint) or hint in domain for hint in COMMUNITY_DOMAINS):
        return "first_hand_community", SOURCE_WEIGHTS["first_hand_community"]
    if any(term in text or term in domain for term in REVIEW_HINTS):
        return "product_review_comment", SOURCE_WEIGHTS["product_review_comment"]
    if any(hint in domain for hint in VENDOR_HINTS):
        if "blog" in source_url.lower() or "resources" in source_url.lower() or "learn" in source_url.lower():
            return "content_marketing", SOURCE_WEIGHTS["content_marketing"]
        return "vendor_blog", SOURCE_WEIGHTS["vendor_blog"]
    if any(term in text for term in WORKAROUND_TERMS):
        return "workaround_discussion", SOURCE_WEIGHTS["workaround_discussion"]
    if "blog" in source_url.lower() or "guide" in text:
        return "practitioner_blog", SOURCE_WEIGHTS["practitioner_blog"]
    if source_url:
        return "generic_article", SOURCE_WEIGHTS["generic_article"]
    return "unknown", SOURCE_WEIGHTS["unknown"]


def source_weight(category: str | None) -> float:
    return SOURCE_WEIGHTS.get(str(category or "unknown"), SOURCE_WEIGHTS["unknown"])
