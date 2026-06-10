from pathlib import Path

import pytest
from pydantic import ValidationError

from demand_radar.calibration.calibration_review import append_calibration_review, load_calibration_reviews
from demand_radar.calibration.calibration_schema import CalibrationReview


def test_calibration_review_can_be_created() -> None:
    review = CalibrationReview(
        review_id="review_000001",
        raw_signal_id="sig_000001",
        normalized_signal_id="norm_000001",
        pain_point_id="pain_000001",
        label="good_extraction",
        reviewer_note="Quote and persona are correct.",
    )

    assert review.review_id == "review_000001"
    assert review.created_at
    assert review.label == "good_extraction"


def test_invalid_calibration_label_is_rejected() -> None:
    with pytest.raises(ValidationError):
        CalibrationReview(
            review_id="review_000001",
            raw_signal_id="sig_000001",
            label="not_a_label",
            reviewer_note="bad",
        )


def test_append_calibration_review_generates_id(tmp_path: Path) -> None:
    reviews_path = tmp_path / "calibration_reviews.jsonl"

    review = append_calibration_review(
        raw_signal_id="sig_000001",
        pain_point_id="pain_000001",
        label="bad_quote",
        reviewer_note="Quote is too narrow.",
        path=reviews_path,
    )

    assert review.review_id == "review_000001"
    assert load_calibration_reviews(reviews_path)[0].label == "bad_quote"
