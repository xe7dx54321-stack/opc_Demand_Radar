"""Persistence helpers for human extraction calibration reviews."""

from __future__ import annotations

from pathlib import Path

from demand_radar.calibration.calibration_schema import CalibrationReview
from demand_radar.state.raw_store import next_id, read_jsonl, write_jsonl


DEFAULT_CALIBRATION_REVIEWS_PATH = "data/processed/calibration_reviews.jsonl"


def append_calibration_review(
    raw_signal_id: str,
    label: str,
    reviewer_note: str,
    path: str | Path = DEFAULT_CALIBRATION_REVIEWS_PATH,
    normalized_signal_id: str | None = None,
    pain_point_id: str | None = None,
    expected_persona: str | None = None,
    expected_evidence_quote: str | None = None,
    expected_pain_description: str | None = None,
    should_be_quarantined: bool | None = None,
) -> CalibrationReview:
    existing_reviews = load_calibration_reviews(path)
    review = CalibrationReview(
        review_id=next_id("review", [item.review_id for item in existing_reviews]),
        raw_signal_id=raw_signal_id,
        normalized_signal_id=normalized_signal_id,
        pain_point_id=pain_point_id,
        label=label,
        reviewer_note=reviewer_note,
        expected_persona=expected_persona,
        expected_evidence_quote=expected_evidence_quote,
        expected_pain_description=expected_pain_description,
        should_be_quarantined=should_be_quarantined,
    )
    write_jsonl(path, [review], append=True)
    return review


def load_calibration_reviews(
    path: str | Path = DEFAULT_CALIBRATION_REVIEWS_PATH,
) -> list[CalibrationReview]:
    return [CalibrationReview.model_validate(row) for row in read_jsonl(path)]
