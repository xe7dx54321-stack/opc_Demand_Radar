"""D4 second-round review report tests."""
from __future__ import annotations

import json
from pathlib import Path

from demand_radar.ui.d4_review_schema import D4PainSignalReview
from demand_radar.ui.d4_review_service import build_d4_review_report
from demand_radar.ui.d4_review_store import D4ReviewStore


def _write_pain_items(path: Path) -> None:
    rows = [
        {
            "pain_item_id": "pain__000001",
            "candidate_id": "cand_1",
            "should_extract": True,
            "title": "Manual investment research workflow",
            "source_url": "https://valid.example/research",
            "evidence_strength": "strong",
            "confidence": 0.88,
        },
        {
            "pain_item_id": "pain__000002",
            "candidate_id": "cand_2",
            "should_extract": True,
            "title": "Portfolio monitoring overload",
            "source_url": "https://valid.example/portfolio",
            "evidence_strength": "medium",
            "confidence": 0.78,
        },
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )


def test_d4_review_report_can_generate_summary_and_candidates(tmp_path: Path) -> None:
    pain_path = tmp_path / "foundation_search_pain_items.jsonl"
    report_path = tmp_path / "d4_second_review_report.md"
    store = D4ReviewStore(tmp_path / "d4_reviews.jsonl")
    _write_pain_items(pain_path)
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

    text = build_d4_review_report(
        store=store,
        output_path=report_path,
        pain_items_path=pain_path,
    )

    assert report_path.exists()
    assert "痛点信号总数：2" in text
    assert "已审核：1" in text
    assert "未审核：1" in text
    assert "真痛点：1" in text
    assert "建议继续推进的候选" in text
    assert "Manual investment research workflow" in text
