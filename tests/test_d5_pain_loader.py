"""D5 D4 pain loader tests."""
from __future__ import annotations

from pathlib import Path

from demand_radar.d5.d4_pain_loader import load_d4_pain_items

from tests.test_d5_fixtures import pain_row, review_row, write_jsonl


def test_loads_only_should_extract_true_strengths_and_attaches_reviews(tmp_path: Path) -> None:
    pain_path = tmp_path / "pain.jsonl"
    reviews_path = tmp_path / "reviews.jsonl"
    write_jsonl(
        pain_path,
        [
            pain_row("pain__001", "https://reddit.com/r/vc/a", evidence_strength="strong"),
            pain_row("pain__002", "https://valid.example/b", evidence_strength="weak"),
            {**pain_row("pain__003", "https://valid.example/c"), "should_extract": False},
        ],
    )
    write_jsonl(reviews_path, [review_row("pain__001", true_pain=None, action_decision="needs_more_evidence")])

    rows = load_d4_pain_items(pain_path, reviews_path=reviews_path)

    assert [row["pain_item_id"] for row in rows] == ["pain__001"]
    assert rows[0]["human_review_status"] == "reviewed_needs_more_evidence"
    assert rows[0]["human_true_pain"] is None
