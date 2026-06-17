"""D4 review queue service tests."""
from __future__ import annotations

import json
from pathlib import Path

from demand_radar.ui.d4_review_schema import D4PainSignalReview
from demand_radar.ui.d4_review_store import D4ReviewStore
from demand_radar.ui.review_queue_service import get_queue_stats, load_review_queue


def _write_rows(path: Path) -> None:
    rows = [
        _row("pain_medium_high", "medium", 0.99),
        _row("pain_strong_low", "strong", 0.61),
        _row("pain_weak", "weak", 0.95),
        _row("pain_medium_low", "medium", 0.5),
        {"pain_item_id": "pain_reject", "should_extract": False, "evidence_strength": "strong"},
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )


def _row(pid: str, strength: str, confidence: float) -> dict:
    return {
        "pain_item_id": pid,
        "candidate_id": f"cand_{pid}",
        "should_extract": True,
        "title": pid,
        "evidence_strength": strength,
        "confidence": confidence,
        "source_url": f"https://valid.example/{pid}",
        "metadata": {
            "seed_id": "seed__001",
            "query_type": "manual_workflow",
            "raw_text_source": "full_page",
            "result_domain": "valid.example",
        },
    }


def test_review_queue_loads_only_should_extract_and_sorts_strength_first(tmp_path: Path) -> None:
    path = tmp_path / "pain.jsonl"
    _write_rows(path)

    items = load_review_queue(pain_items_path=path)

    assert [item["pain_item_id"] for item in items] == [
        "pain_strong_low",
        "pain_medium_high",
        "pain_medium_low",
        "pain_weak",
    ]
    assert items[0]["seed_id"] == "seed__001"
    assert items[0]["query_type"] == "manual_workflow"
    assert items[0]["raw_text_source"] == "full_page"
    assert items[0]["result_domain"] == "valid.example"


def test_review_queue_stats_and_unreviewed_filter(tmp_path: Path) -> None:
    path = tmp_path / "pain.jsonl"
    reviews_path = tmp_path / "reviews.jsonl"
    _write_rows(path)
    store = D4ReviewStore(reviews_path)
    store.upsert_review(
        D4PainSignalReview(
            review_id="d4_review_000001",
            pain_item_id="pain_strong_low",
            candidate_id="cand_pain_strong_low",
            true_pain=True,
            commercial_potential="high",
            evidence_quality="strong",
            action_decision="pursue",
            extraction_quality="good",
            created_at="2026-06-17T00:00:00Z",
        )
    )

    stats = get_queue_stats(store, pain_items_path=path)
    unreviewed = load_review_queue(
        store=store,
        filter_unreviewed_only=True,
        pain_items_path=path,
    )

    assert stats["total"] == 4
    assert stats["strong"] == 1
    assert stats["medium"] == 2
    assert stats["weak"] == 1
    assert stats["reviewed"] == 1
    assert stats["unreviewed"] == 3
    assert "pain_strong_low" not in {item["pain_item_id"] for item in unreviewed}
