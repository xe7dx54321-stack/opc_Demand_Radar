"""Build a small human review queue from D5 demand themes."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from demand_radar.d5.io_utils import load_config, output_path, write_jsonl
from demand_radar.d5.theme_schema import DemandTheme, ThemeReviewQueueItem
from demand_radar.state.raw_store import next_ids, utc_now_iso


def build_theme_review_queue(
    themes: list[DemandTheme],
    config_path: Path | str | None = None,
    output_path_value: Path | str | None = None,
    report_path: Path | str | None = None,
) -> list[ThemeReviewQueueItem]:
    cfg = load_config(config_path)
    out_path = Path(output_path_value) if output_path_value else output_path(
        cfg,
        "theme_review_queue_path",
        "data/processed/d5/theme_review_queue.jsonl",
    )
    report_out = Path(report_path) if report_path else output_path(
        cfg,
        "theme_review_queue_report_path",
        "outputs/d5/theme_review_queue_report.md",
    )
    queue_ids = next_ids("theme_queue", [], len(themes))
    queue_items = [_queue_item(theme, queue_ids[idx]) for idx, theme in enumerate(themes)]
    queue_items.sort(key=_queue_sort_key)
    write_jsonl(out_path, queue_items)
    _write_report(queue_items, report_out)
    return queue_items


def _queue_item(theme: DemandTheme, queue_item_id: str) -> ThemeReviewQueueItem:
    priority = _priority(theme.action_recommendation)
    return ThemeReviewQueueItem(
        queue_item_id=queue_item_id,
        theme_id=theme.theme_id,
        theme_title_zh=theme.theme_title_zh,
        core_pain_zh=theme.core_pain_zh,
        persona_group=theme.persona_group,
        workflow_group=theme.workflow_group,
        action_recommendation=theme.action_recommendation,
        commercial_potential=theme.commercial_potential,
        evidence_quality=theme.evidence_quality,
        confidence=theme.confidence,
        evidence_count=theme.evidence_count,
        unique_domain_count=theme.unique_domain_count,
        first_hand_evidence_count=theme.first_hand_evidence_count,
        reviewed_pursue_count=theme.reviewed_pursue_count,
        representative_quotes=theme.representative_quotes[:5],
        representative_source_urls=theme.representative_source_urls[:5],
        priority=priority,
        review_reason_zh=theme.recommendation_reason_zh,
        created_at=utc_now_iso(),
        metadata={"source_group_ids": theme.source_group_ids, "deduped_item_ids": theme.deduped_item_ids},
    )


def _queue_sort_key(item: ThemeReviewQueueItem) -> tuple[int, float, int, int, str]:
    priority_rank = {"high": 0, "medium": 1, "low": 2}.get(item.priority, 9)
    return (
        priority_rank,
        -float(item.confidence or 0),
        -int(item.first_hand_evidence_count or 0),
        -int(item.reviewed_pursue_count or 0),
        str(item.theme_title_zh or ""),
    )


def _priority(action_recommendation: str) -> str:
    if action_recommendation == "pursue_candidate":
        return "high"
    if action_recommendation == "watch":
        return "medium"
    return "low"


def build_theme_review_queue_report(queue_items: list[ThemeReviewQueueItem], report_path: Path) -> None:
    _write_report(queue_items, report_path)


def _write_report(queue_items: list[ThemeReviewQueueItem], report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    counts = Counter(item.priority for item in queue_items)
    lines = [
        "# D5 Theme Review Queue Report",
        "",
        f"- queue_count: {len(queue_items)}",
        f"- high_priority: {counts.get('high', 0)}",
        f"- medium_priority: {counts.get('medium', 0)}",
        f"- low_priority: {counts.get('low', 0)}",
        "",
    ]
    for item in queue_items:
        lines.extend(
            [
                f"## {item.theme_title_zh}",
                f"- theme_id: {item.theme_id}",
                f"- queue_item_id: {item.queue_item_id}",
                f"- priority: {item.priority}",
                f"- action_recommendation: {item.action_recommendation}",
                f"- commercial_potential: {item.commercial_potential}",
                f"- evidence_quality: {item.evidence_quality}",
                f"- confidence: {item.confidence}",
                f"- evidence_count: {item.evidence_count}",
                f"- unique_domain_count: {item.unique_domain_count}",
                f"- first_hand_evidence_count: {item.first_hand_evidence_count}",
                f"- reviewed_pursue_count: {item.reviewed_pursue_count}",
                f"- representative_source_urls: {', '.join(item.representative_source_urls) if item.representative_source_urls else 'n/a'}",
                "",
                item.review_reason_zh,
                "",
            ]
        )
    if not queue_items:
        lines.append("No theme review queue items generated.")
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

