"""UI service for MVP-C pain signal review."""
from __future__ import annotations
from demand_radar.mvp_c.review_service import ReviewService
from demand_radar.mvp_c.review_store import PainSignalReviewStore


def get_review_service() -> ReviewService:
    return ReviewService()


def get_review_summary() -> dict:
    svc = ReviewService()
    summary = svc.get_summary()
    return summary.model_dump()


def get_pain_signal_cards(
    filter_strength: str | None = None,
    filter_action: str | None = None,
    reviewed_only: bool | None = None,
) -> list[dict]:
    svc = ReviewService()
    cards = svc.load_pain_signal_cards(
        filter_strength=filter_strength,
        filter_action=filter_action,
        reviewed_only=reviewed_only,
    )
    result = []
    for c in cards:
        d = {
            "pain_item_id": c.pain_item_id,
            "candidate_id": c.candidate_id,
            "title": c.title,
            "source_url": c.source_url,
            "source_type": c.source_type,
            "persona": c.persona,
            "workflow_stage": c.workflow_stage,
            "pain_type": c.pain_type,
            "pain_description_zh": c.pain_description_zh,
            "evidence_quote": c.evidence_quote,
            "current_solution": c.current_solution,
            "commercial_signal_type": c.commercial_signal_type,
            "evidence_strength": c.evidence_strength,
            "confidence": c.confidence,
            "reasoning_summary_zh": c.reasoning_summary_zh,
            "existing_review": c.existing_review.model_dump() if c.existing_review else None,
        }
        result.append(d)
    return result
