"""D5 schema tests."""
from __future__ import annotations

import pytest

from demand_radar.d5.theme_schema import DedupedPainItem


def test_deduped_pain_item_accepts_unknown_human_review_status() -> None:
    item = DedupedPainItem(
        deduped_item_id="deduped_item_000001",
        pain_item_id="pain__001",
        evidence_strength="strong",
        confidence=0.8,
        human_review_status="unknown",
        created_at="2026-06-17T00:00:00Z",
    )

    assert item.human_review_status == "unknown"


def test_deduped_pain_item_rejects_invalid_confidence() -> None:
    with pytest.raises(ValueError):
        DedupedPainItem(
            deduped_item_id="deduped_item_000001",
            pain_item_id="pain__001",
            evidence_strength="strong",
            confidence=1.5,
            human_review_status="unreviewed",
            created_at="2026-06-17T00:00:00Z",
        )
