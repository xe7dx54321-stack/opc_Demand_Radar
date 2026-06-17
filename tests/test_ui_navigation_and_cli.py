"""CLI coverage for D4 review console."""
from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from demand_radar.cli import app
from demand_radar.ui.d4_review_schema import D4PainSignalReview
from demand_radar.ui.d4_review_store import D4ReviewStore


def test_cli_build_d4_review_report(tmp_path: Path, monkeypatch) -> None:
    store = D4ReviewStore(tmp_path / "d4_reviews.jsonl")
    store.upsert_review(
        D4PainSignalReview(
            review_id="d4_review_000001",
            pain_item_id="pain__000001",
            candidate_id="cand_1",
            source_url="https://valid.example/research",
            true_pain=True,
            commercial_potential="high",
            evidence_quality="strong",
            action_decision="pursue",
            extraction_quality="good",
            created_at="2026-06-17T00:00:00Z",
        )
    )
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    result = runner.invoke(app, ["build-d4-review-report"])

    assert result.exit_code == 0
    assert Path("outputs/reviews/d4_second_review_report.md").exists()
