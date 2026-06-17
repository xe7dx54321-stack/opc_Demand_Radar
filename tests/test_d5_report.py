"""D5 report tests."""
from __future__ import annotations

from pathlib import Path

from demand_radar.d5.d5_pipeline import run_d5

from tests.test_d5_fixtures import pain_row, review_row, write_config, write_jsonl


def test_d5_pipeline_generates_reports_and_gracefully_handles_inputs(tmp_path: Path) -> None:
    pain_path = tmp_path / "pain.jsonl"
    reviews_path = tmp_path / "reviews.jsonl"
    write_jsonl(
        pain_path,
        [
            pain_row("pain__001", "https://www.reddit.com/r/vc/a", workflow_stage="deal sourcing"),
            pain_row("pain__002", "https://b.example/2", workflow_stage="deal sourcing"),
            pain_row("pain__003", "https://c.example/3", workflow_stage="deal sourcing"),
        ],
    )
    write_jsonl(reviews_path, [review_row("pain__001", action_decision="pursue")])
    config = write_config(tmp_path, pain_path, reviews_path)

    summary = run_d5(config_path=config)

    assert summary.engineering_acceptance == "pass"
    assert summary.theme_count == 1
    assert (tmp_path / "summary.md").exists()
    assert (tmp_path / "themes.md").exists()
    assert "Demand Themes" in (tmp_path / "summary.md").read_text(encoding="utf-8")


def test_d5_pipeline_graceful_when_no_d4_data(tmp_path: Path) -> None:
    pain_path = tmp_path / "empty.jsonl"
    reviews_path = tmp_path / "reviews.jsonl"
    write_jsonl(pain_path, [])
    write_jsonl(reviews_path, [])
    config = write_config(tmp_path, pain_path, reviews_path)

    summary = run_d5(config_path=config)

    assert summary.engineering_acceptance == "partial"
    assert summary.can_enter_theme_review is False
