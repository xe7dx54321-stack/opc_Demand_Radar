"""UI helper service for Stage 3 Truth Score review."""
from __future__ import annotations

from demand_radar.state.raw_store import next_ids, utc_now_iso
from demand_radar.truth_scoring.truth_schema import TruthScore, TruthScoreReview
from demand_radar.truth_scoring.truth_store import (
    append_truth_score_review,
    load_truth_score_reviews,
    load_truth_scores,
)


def get_truth_scores() -> list[TruthScore]:
    """Return all persisted TruthScore records."""
    return load_truth_scores()


def submit_truth_review(
    truth_score_id: str,
    source_group_id: str,
    label: str,
    reviewer_note: str | None = None,
    corrected_truth_level: str | None = None,
    corrected_next_action: str | None = None,
) -> TruthScoreReview:
    """Create and persist a TruthScoreReview record."""
    existing = load_truth_score_reviews()
    existing_ids = [r.review_id for r in existing]
    review_id = next_ids("truth_score_review", existing_ids, 1)[0]

    review = TruthScoreReview(
        review_id=review_id,
        truth_score_id=truth_score_id,
        source_group_id=source_group_id,
        label=label,
        reviewer_note=reviewer_note,
        corrected_truth_level=corrected_truth_level,
        corrected_next_action=corrected_next_action,
        created_at=utc_now_iso(),
    )
    append_truth_score_review(review)
    return review
