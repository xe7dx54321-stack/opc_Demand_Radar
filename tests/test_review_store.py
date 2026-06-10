from pathlib import Path

from demand_radar.calibration.review_store import append_review, get_latest_review_for_item, load_reviews


def test_load_reviews_empty_file_is_safe(tmp_path: Path) -> None:
    reviews_path = tmp_path / "reviews.jsonl"

    assert load_reviews(reviews_path) == []
    assert get_latest_review_for_item("sig_000001", path=reviews_path) is None


def test_append_review_writes_jsonl_and_allows_duplicates(tmp_path: Path) -> None:
    reviews_path = tmp_path / "reviews.jsonl"

    first = append_review(
        raw_signal_id="sig_000001",
        normalized_signal_id="norm_000001",
        pain_point_id="pain_000001",
        label="weak_extraction",
        reviewer_note="Quote is useful but thin.",
        path=reviews_path,
    )
    second = append_review(
        raw_signal_id="sig_000001",
        normalized_signal_id="norm_000001",
        pain_point_id="pain_000001",
        label="bad_quote",
        reviewer_note="Latest review should win.",
        path=reviews_path,
    )

    reviews = load_reviews(reviews_path)
    latest = get_latest_review_for_item(
        "sig_000001",
        normalized_signal_id="norm_000001",
        pain_point_id="pain_000001",
        path=reviews_path,
    )
    assert [review.review_id for review in reviews] == [first.review_id, second.review_id]
    assert latest is not None
    assert latest.label == "bad_quote"


def test_latest_review_can_match_raw_only_item(tmp_path: Path) -> None:
    reviews_path = tmp_path / "reviews.jsonl"
    append_review(
        raw_signal_id="sig_000001",
        label="false_negative",
        reviewer_note="Raw signal contains pain but no pain point exists.",
        path=reviews_path,
    )

    latest = get_latest_review_for_item("sig_000001", path=reviews_path)

    assert latest is not None
    assert latest.label == "false_negative"
