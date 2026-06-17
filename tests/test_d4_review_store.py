"""D4 review store tests."""
from __future__ import annotations

from pathlib import Path

from demand_radar.ui.d4_review_schema import D4PainSignalReview
from demand_radar.ui.d4_review_store import D4ReviewStore


def _review(pid: str = "pain__000001", action: str = "watch") -> D4PainSignalReview:
    return D4PainSignalReview(
        review_id=f"d4_review_{pid}",
        pain_item_id=pid,
        candidate_id=f"cand_{pid}",
        source_url="https://valid.example/pain",
        true_pain=True,
        commercial_potential="medium",
        evidence_quality="strong",
        action_decision=action,
        extraction_quality="good",
        error_labels=[],
        created_at="2026-06-17T00:00:00Z",
    )


def test_d4_review_upsert_overwrites_by_pain_item_id(tmp_path: Path) -> None:
    store = D4ReviewStore(tmp_path / "d4_reviews.jsonl")

    store.upsert_review(_review("pain__000001", "watch"))
    store.upsert_review(_review("pain__000001", "pursue"))

    reviews = store.load_reviews()
    assert len(reviews) == 1
    assert reviews[0].pain_item_id == "pain__000001"
    assert reviews[0].action_decision == "pursue"


def test_d4_review_store_does_not_pollute_mvp_c_review_file(tmp_path: Path) -> None:
    mvp_c_path = tmp_path / "pain_signal_reviews.jsonl"
    mvp_c_path.write_text('{"review_id":"mvpc_original"}\n', encoding="utf-8")
    store = D4ReviewStore(tmp_path / "reviews" / "d4_pain_signal_reviews.jsonl")

    store.upsert_review(_review())

    assert mvp_c_path.read_text(encoding="utf-8") == '{"review_id":"mvpc_original"}\n'
    assert store.path.name == "d4_pain_signal_reviews.jsonl"


def test_d4_review_summary_counts_actions_and_commercial(tmp_path: Path) -> None:
    store = D4ReviewStore(tmp_path / "d4_reviews.jsonl")
    store.upsert_review(_review("pain__000001", "pursue"))
    store.upsert_review(_review("pain__000002", "watch"))

    summary = store.summary()

    assert summary["total"] == 2
    assert summary["true_pain"] == 2
    assert summary["pursue"] == 1
    assert summary["watch"] == 1
    assert summary["commercial_medium"] == 2
