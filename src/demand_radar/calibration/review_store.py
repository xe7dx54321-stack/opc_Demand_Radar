"""Review storage helpers for Stage 1.6 UI workflows."""

from __future__ import annotations

from pathlib import Path

from demand_radar.calibration.calibration_review import (
    DEFAULT_CALIBRATION_REVIEWS_PATH,
    append_calibration_review,
    load_calibration_reviews,
)
from demand_radar.calibration.calibration_schema import CalibrationReview


def append_review(
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
    return append_calibration_review(
        raw_signal_id=raw_signal_id,
        normalized_signal_id=normalized_signal_id,
        pain_point_id=pain_point_id,
        label=label,
        reviewer_note=reviewer_note,
        expected_persona=expected_persona,
        expected_evidence_quote=expected_evidence_quote,
        expected_pain_description=expected_pain_description,
        should_be_quarantined=should_be_quarantined,
        path=path,
    )


def load_reviews(path: str | Path = DEFAULT_CALIBRATION_REVIEWS_PATH) -> list[CalibrationReview]:
    return load_calibration_reviews(path)


def get_latest_review_for_item(
    raw_signal_id: str,
    normalized_signal_id: str | None = None,
    pain_point_id: str | None = None,
    reviews: list[CalibrationReview] | None = None,
    path: str | Path = DEFAULT_CALIBRATION_REVIEWS_PATH,
) -> CalibrationReview | None:
    review_list = reviews if reviews is not None else load_reviews(path)
    matching = [
        review
        for review in review_list
        if _review_matches_item(review, raw_signal_id, normalized_signal_id, pain_point_id)
    ]
    if not matching:
        return None
    return matching[-1]


def _review_matches_item(
    review: CalibrationReview,
    raw_signal_id: str,
    normalized_signal_id: str | None,
    pain_point_id: str | None,
) -> bool:
    if pain_point_id:
        return review.pain_point_id == pain_point_id
    if normalized_signal_id:
        return review.pain_point_id is None and review.normalized_signal_id == normalized_signal_id
    return review.pain_point_id is None and review.normalized_signal_id is None and review.raw_signal_id == raw_signal_id
