"""Load D4 second-round review samples for D5 calibration."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from demand_radar.d5.io_utils import read_jsonl

DEFAULT_D4_REVIEWS_PATH = Path("data/processed/reviews/d4_pain_signal_reviews.jsonl")


def load_d4_reviews(path: Path | str | None = None) -> list[dict[str, Any]]:
    """Load D4 reviews without touching MVP-C review files."""
    return read_jsonl(path or DEFAULT_D4_REVIEWS_PATH)


def build_review_lookup(path: Path | str | None = None) -> dict[str, dict[str, Any]]:
    """Return the latest D4 review per pain_item_id."""
    reviews = load_d4_reviews(path)
    lookup: dict[str, dict[str, Any]] = {}
    for review in reviews:
        pain_item_id = str(review.get("pain_item_id") or "")
        if pain_item_id:
            lookup[pain_item_id] = review
    return lookup


def human_review_status(review: dict[str, Any] | None) -> str:
    """Translate a D4 review into D5's non-destructive calibration status.

    A blank ``true_pain`` is intentionally treated as unknown, never as false.
    """
    if not review:
        return "unreviewed"
    if review.get("true_pain") is False or review.get("action_decision") == "reject":
        return "reviewed_reject"
    if review.get("action_decision") == "needs_more_evidence":
        return "reviewed_needs_more_evidence"
    if review.get("true_pain") is True or review.get("action_decision") in {"pursue", "watch"}:
        return "reviewed_positive"
    return "unknown"

