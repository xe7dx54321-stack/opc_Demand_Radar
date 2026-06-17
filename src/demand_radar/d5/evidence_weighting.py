"""Evidence weighting helpers for D5."""
from __future__ import annotations

from demand_radar.d5.source_classifier import source_weight


STRENGTH_WEIGHTS = {
    "strong": 1.0,
    "medium": 0.7,
    "weak": 0.35,
}


def evidence_weight(evidence_strength: str | None, source_category: str | None) -> float:
    """Combine extraction strength and source category into a lightweight score."""
    return round(
        STRENGTH_WEIGHTS.get(str(evidence_strength or "weak"), 0.35)
        * source_weight(source_category),
        3,
    )


def source_diversity(unique_domain_count: int) -> str:
    if unique_domain_count >= 4:
        return "high"
    if unique_domain_count >= 2:
        return "medium"
    return "low"


def evidence_quality(strong_count: int, medium_count: int, weak_count: int) -> str:
    if strong_count >= 2:
        return "strong"
    if strong_count >= 1 and medium_count >= 1:
        return "mixed"
    if medium_count >= 2:
        return "medium"
    if strong_count >= 1:
        return "strong"
    if medium_count >= 1:
        return "medium"
    if weak_count >= 1:
        return "weak"
    return "weak"

