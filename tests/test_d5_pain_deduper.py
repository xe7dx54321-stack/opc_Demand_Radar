"""D5 pain deduper tests."""
from __future__ import annotations

from pathlib import Path

from demand_radar.d5.pain_deduper import dedupe_pain_items

from tests.test_d5_fixtures import pain_row, review_row, write_config, write_jsonl


def test_same_source_url_is_grouped_and_one_representative_selected(tmp_path: Path) -> None:
    pain_path = tmp_path / "pain.jsonl"
    reviews_path = tmp_path / "reviews.jsonl"
    source_url = "https://www.reddit.com/r/vc/comments/a"
    write_jsonl(
        pain_path,
        [
            pain_row("pain__001", source_url, confidence=0.7),
            pain_row("pain__002", source_url, confidence=0.95),
            pain_row("pain__003", "https://other.example/research", confidence=0.6),
        ],
    )
    write_jsonl(reviews_path, [review_row("pain__001", action_decision="pursue")])
    config = write_config(tmp_path, pain_path, reviews_path)

    deduped, groups, summary = dedupe_pain_items(config_path=config)

    assert len(deduped) == 3
    assert len(groups) == 2
    assert summary["duplicate_groups"] == 1
    assert sum(1 for item in deduped if item.source_url == source_url and item.is_representative) == 1
    assert all(group.evidence_count <= 2 for group in groups)
