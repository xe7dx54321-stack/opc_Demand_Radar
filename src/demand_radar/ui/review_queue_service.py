"""Review queue service for D4 pain-signal review."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from demand_radar.ui.current_task_service import D4_PAIN_PATH, load_d4_pain_signals
from demand_radar.ui.d4_review_store import D4ReviewStore

STRENGTH_ORDER = {"strong": 0, "medium": 1, "weak": 2}


def normalize_review_queue_item(item: dict[str, Any]) -> dict[str, Any]:
    """Flatten common metadata fields so the UI can render D4 cards consistently."""
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    normalized = dict(item)
    for key in (
        "seed_id",
        "pain_item_id",
        "query_id",
        "query",
        "query_type",
        "raw_text_source",
        "result_domain",
        "source_category",
    ):
        if not normalized.get(key) and metadata.get(key):
            normalized[key] = metadata[key]
    normalized.setdefault("raw_text_source", metadata.get("raw_text_source"))
    normalized.setdefault("result_domain", metadata.get("result_domain"))
    normalized.setdefault("query_type", metadata.get("query_type"))
    normalized.setdefault("seed_id", metadata.get("seed_id"))
    return normalized


def load_review_queue(
    store: D4ReviewStore | None = None,
    filter_unreviewed_only: bool = False,
    min_strength: str | None = None,
    pain_items_path: Path | str | None = None,
) -> list[dict[str, Any]]:
    """Load D4 pain signals for review, sorted strong -> medium -> weak."""
    items = [
        normalize_review_queue_item(item)
        for item in load_d4_pain_signals(pain_items_path or D4_PAIN_PATH)
    ]

    if min_strength and min_strength != "全部":
        if min_strength == "strong":
            allowed = {"strong"}
        elif min_strength == "medium":
            allowed = {"strong", "medium"}
        elif min_strength == "weak":
            allowed = {"strong", "medium", "weak"}
        else:
            allowed = {min_strength}
        items = [item for item in items if item.get("evidence_strength") in allowed]

    if filter_unreviewed_only and store is not None:
        reviewed_ids = store.get_reviewed_ids()
        items = [item for item in items if item.get("pain_item_id") not in reviewed_ids]

    items.sort(
        key=lambda item: (
            STRENGTH_ORDER.get(str(item.get("evidence_strength") or "weak"), 9),
            -float(item.get("confidence") or 0),
            str(item.get("pain_item_id") or ""),
        )
    )
    return items


def get_queue_stats(
    store: D4ReviewStore | None = None,
    pain_items_path: Path | str | None = None,
) -> dict[str, int]:
    """Return counts for the review queue header."""
    items = load_review_queue(
        store=None,
        filter_unreviewed_only=False,
        pain_items_path=pain_items_path or D4_PAIN_PATH,
    )
    reviewed_ids = store.get_reviewed_ids() if store else set()
    reviewed = sum(1 for item in items if item.get("pain_item_id") in reviewed_ids)
    return {
        "total": len(items),
        "strong": sum(1 for item in items if item.get("evidence_strength") == "strong"),
        "medium": sum(1 for item in items if item.get("evidence_strength") == "medium"),
        "weak": sum(1 for item in items if item.get("evidence_strength") == "weak"),
        "reviewed": reviewed,
        "unreviewed": len(items) - reviewed,
    }
