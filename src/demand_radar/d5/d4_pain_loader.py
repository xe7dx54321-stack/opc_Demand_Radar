"""Load and normalize D4 pain items for D5."""
from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from demand_radar.d5.d4_review_loader import build_review_lookup, human_review_status
from demand_radar.d5.io_utils import read_jsonl

DEFAULT_D4_PAIN_ITEMS_PATH = Path("data/processed/mvp_d4/foundation_search_pain_items.jsonl")
DEFAULT_INCLUDE_STRENGTHS = {"strong", "medium"}


def load_d4_pain_items(
    path: Path | str | None = None,
    include_strengths: set[str] | None = None,
    reviews_path: Path | str | None = None,
) -> list[dict[str, Any]]:
    """Load D4 pain items that should be considered for D5 themes."""
    include = include_strengths or DEFAULT_INCLUDE_STRENGTHS
    rows = read_jsonl(path or DEFAULT_D4_PAIN_ITEMS_PATH)
    review_lookup = build_review_lookup(reviews_path)
    items: list[dict[str, Any]] = []
    for row in rows:
        if row.get("should_extract") is not True:
            continue
        if str(row.get("evidence_strength") or "") not in include:
            continue
        item = normalize_d4_pain_item(row)
        review = review_lookup.get(str(item.get("pain_item_id") or ""))
        item["human_review_status"] = human_review_status(review)
        item["human_action_decision"] = review.get("action_decision") if review else None
        item["human_commercial_potential"] = review.get("commercial_potential") if review else None
        item["human_true_pain"] = review.get("true_pain") if review else None
        item["human_evidence_quality"] = review.get("evidence_quality") if review else None
        item["human_extraction_quality"] = review.get("extraction_quality") if review else None
        items.append(item)
    return items


def load_all_d4_pain_items(path: Path | str | None = None) -> list[dict[str, Any]]:
    """Load all D4 pain rows for input summary, including rejected and weak rows."""
    return read_jsonl(path or DEFAULT_D4_PAIN_ITEMS_PATH)


def normalize_d4_pain_item(row: dict[str, Any]) -> dict[str, Any]:
    """Flatten useful metadata and derive result_domain."""
    metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    item = dict(row)
    for key in (
        "seed_id",
        "query_id",
        "query",
        "query_type",
        "raw_text_source",
        "result_domain",
        "source_category",
    ):
        if not item.get(key) and metadata.get(key):
            item[key] = metadata[key]
    source_url = str(item.get("source_url") or "")
    if not item.get("result_domain"):
        item["result_domain"] = urlparse(source_url).netloc.lower() if source_url else None
    return item

