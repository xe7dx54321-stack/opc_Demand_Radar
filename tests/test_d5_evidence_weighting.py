"""D5 evidence weighting tests."""
from __future__ import annotations

from demand_radar.d5.evidence_weighting import evidence_quality, evidence_weight, source_diversity


def test_source_weight_orders_first_hand_above_vendor() -> None:
    assert evidence_weight("strong", "first_hand_community") > evidence_weight("strong", "content_marketing")
    assert evidence_weight("medium", "workaround_discussion") > evidence_weight("medium", "technical_issue")


def test_quality_and_diversity_buckets() -> None:
    assert evidence_quality(2, 0, 0) == "strong"
    assert evidence_quality(0, 2, 0) == "medium"
    assert source_diversity(4) == "high"
    assert source_diversity(1) == "low"
