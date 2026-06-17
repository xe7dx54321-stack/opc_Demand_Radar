"""D5 theme review queue tests."""
from __future__ import annotations

from demand_radar.d5.theme_review_queue import build_theme_review_queue
from demand_radar.d5.theme_schema import DemandTheme


def _theme(theme_id: str, action: str, confidence: float, first_hand: int = 0, pursue: int = 0) -> DemandTheme:
    return DemandTheme(
        theme_id=theme_id,
        theme_title_zh=theme_id,
        core_pain_zh="核心痛点",
        deduped_item_ids=[theme_id],
        source_group_ids=[theme_id],
        evidence_count=3,
        unique_source_url_count=3,
        unique_domain_count=3,
        strong_count=1,
        medium_count=2,
        weak_count=0,
        first_hand_evidence_count=first_hand,
        workaround_evidence_count=0,
        marketing_or_vendor_evidence_count=0,
        job_description_evidence_count=0,
        reviewed_positive_count=0,
        reviewed_pursue_count=pursue,
        reviewed_watch_count=0,
        reviewed_needs_more_evidence_count=0,
        reviewed_reject_count=0,
        commercial_potential="medium",
        evidence_quality="strong",
        source_diversity="medium",
        confidence=confidence,
        action_recommendation=action,
        recommendation_reason_zh="理由",
        created_at="2026-06-17T00:00:00Z",
    )


def test_theme_review_queue_prioritizes_pursue_then_watch(tmp_path) -> None:
    out = tmp_path / "queue.jsonl"
    report = tmp_path / "queue.md"
    queue = build_theme_review_queue(
        [
            _theme("theme_watch", "watch", 0.9),
            _theme("theme_pursue", "pursue_candidate", 0.5, first_hand=1, pursue=1),
            _theme("theme_more", "needs_more_evidence", 0.95),
        ],
        output_path_value=out,
        report_path=report,
    )

    assert [item.theme_id for item in queue] == ["theme_pursue", "theme_watch", "theme_more"]
    assert queue[0].priority == "high"
    assert report.exists()
