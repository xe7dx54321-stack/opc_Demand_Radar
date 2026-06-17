"""D5 D4 review loader tests."""
from __future__ import annotations

from pathlib import Path

from demand_radar.d5.d4_review_loader import build_review_lookup, human_review_status, load_d4_reviews

from tests.test_d5_fixtures import review_row, write_jsonl


def test_load_d4_reviews_from_separate_file_does_not_require_mvp_c(tmp_path: Path) -> None:
    d4_path = tmp_path / "reviews" / "d4_pain_signal_reviews.jsonl"
    mvp_c_path = tmp_path / "pain_signal_reviews.jsonl"
    mvp_c_path.write_text('{"review_id":"mvp_c"}\n', encoding="utf-8")
    write_jsonl(d4_path, [review_row("pain__001")])

    reviews = load_d4_reviews(d4_path)

    assert len(reviews) == 1
    assert build_review_lookup(d4_path)["pain__001"]["action_decision"] == "pursue"
    assert mvp_c_path.read_text(encoding="utf-8") == '{"review_id":"mvp_c"}\n'


def test_blank_true_pain_is_unknown_not_false() -> None:
    assert human_review_status(review_row("pain__001", true_pain=None, action_decision="")) == "unknown"
