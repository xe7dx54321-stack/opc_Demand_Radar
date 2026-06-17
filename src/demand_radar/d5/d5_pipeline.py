"""D5 pipeline: consolidate D4 pain evidence into demand themes."""
from __future__ import annotations

import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

from demand_radar.d5.d4_pain_loader import load_all_d4_pain_items, load_d4_pain_items
from demand_radar.d5.d4_review_loader import load_d4_reviews
from demand_radar.d5.d5_report import build_d5_summary_report
from demand_radar.d5.io_utils import input_path, load_config, output_path
from demand_radar.d5.pain_deduper import dedupe_pain_items
from demand_radar.d5.theme_grouper import build_demand_themes
from demand_radar.d5.theme_review_queue import build_theme_review_queue
from demand_radar.d5.theme_schema import D5RunSummary
from demand_radar.state.raw_store import utc_now_iso


def run_d5(
    domain_id: str = "ai_investment_tracking",
    config_path: Path | str | None = None,
    llm_client: Any | None = None,
) -> D5RunSummary:
    cfg = load_config(config_path)
    pain_items_path = input_path(
        cfg,
        "d4_pain_items_path",
        "data/processed/mvp_d4/foundation_search_pain_items.jsonl",
    )
    reviews_path = input_path(
        cfg,
        "d4_reviews_path",
        "data/processed/reviews/d4_pain_signal_reviews.jsonl",
    )
    all_d4_items = load_all_d4_pain_items(pain_items_path)
    reviewable_items = [row for row in all_d4_items if row.get("should_extract") is True]
    reviews = load_d4_reviews(reviews_path)

    deduped_items, source_groups, dedupe_summary = dedupe_pain_items(
        config_path=config_path,
        pain_items_path=pain_items_path,
        reviews_path=reviews_path,
    )
    themes = build_demand_themes(
        config_path=config_path,
        reviews_path=reviews_path,
        llm_client=llm_client,
    )
    queue_items = build_theme_review_queue(themes, config_path=config_path)

    source_category_counts = Counter(group.source_category for group in source_groups)
    queue_priority_counts = Counter(item.priority for item in queue_items)
    review_action_counts = Counter(str(row.get("action_decision") or "unknown") for row in reviews)
    strength_counts = Counter(str(row.get("evidence_strength") or "unknown") for row in reviewable_items)
    engineering_acceptance, product_acceptance, can_theme_review, can_product_discovery, reason = _acceptance(
        themes_count=len(themes),
        representative_count=dedupe_summary["deduped_representatives"],
        queue_count=len(queue_items),
        duplicate_groups=dedupe_summary["duplicate_groups"],
        themes=themes,
    )
    summary = D5RunSummary(
        domain_id=domain_id,
        generated_at=utc_now_iso(),
        radar_commit=_git_commit(),
        input_pain_items_path=str(pain_items_path),
        input_reviews_path=str(reviews_path),
        total_d4_pain_items=len(all_d4_items),
        should_extract_true=len(reviewable_items),
        strong=strength_counts.get("strong", 0),
        medium=strength_counts.get("medium", 0),
        weak=strength_counts.get("weak", 0),
        reviewed_count=len(reviews),
        reviewed_pursue=review_action_counts.get("pursue", 0),
        reviewed_needs_more_evidence=review_action_counts.get("needs_more_evidence", 0),
        reviewed_reject=review_action_counts.get("reject", 0),
        original_items=dedupe_summary["original_pain_items"],
        deduped_representatives=dedupe_summary["deduped_representatives"],
        duplicate_groups=dedupe_summary["duplicate_groups"],
        theme_count=len(themes),
        queue_count=len(queue_items),
        engineering_acceptance=engineering_acceptance,
        product_acceptance=product_acceptance,
        can_enter_theme_review=can_theme_review,
        can_enter_product_discovery=can_product_discovery,
        reason=reason,
        metadata={
            **dedupe_summary,
            **dict(source_category_counts),
            "high_priority": queue_priority_counts.get("high", 0),
            "medium_priority": queue_priority_counts.get("medium", 0),
            "low_priority": queue_priority_counts.get("low", 0),
            "themes": [_theme_summary_row(theme) for theme in themes],
        },
    )
    build_d5_summary_report(
        summary,
        report_path=output_path(cfg, "d5_summary_report_path", "outputs/d5/d5_summary_report.md"),
        metadata=summary.metadata,
    )
    _merge_run_summary(
        {
            "d5_engineering_acceptance": summary.engineering_acceptance,
            "d5_product_acceptance": summary.product_acceptance,
            "d5_theme_count": summary.theme_count,
            "d5_queue_count": summary.queue_count,
            "d5_can_enter_theme_review": summary.can_enter_theme_review,
            "d5_can_enter_product_discovery": summary.can_enter_product_discovery,
            "d5_reason": summary.reason,
        }
    )
    return summary


def build_d5_report_from_stored(domain_id: str = "ai_investment_tracking") -> D5RunSummary:
    """Rebuild D5 outputs from stored D4 inputs."""
    return run_d5(domain_id=domain_id)


def _acceptance(
    themes_count: int,
    representative_count: int,
    queue_count: int,
    duplicate_groups: int,
    themes: list[Any],
) -> tuple[str, str, bool, bool, str]:
    has_actionable_theme = any(
        theme.action_recommendation in {"pursue_candidate", "watch"} for theme in themes
    )
    has_no_duplicate_amplification = representative_count <= 20
    engineering_ok = representative_count > 0 and themes_count > 0 and queue_count > 0
    product_ok = (
        3 <= themes_count <= 5
        and has_actionable_theme
        and has_no_duplicate_amplification
    )
    if engineering_ok and product_ok:
        return (
            "pass",
            "pass",
            True,
            any(theme.action_recommendation == "pursue_candidate" for theme in themes),
            "D4 单条痛点已合并为可审核需求主题，且同源重复未被重复放大。",
        )
    if engineering_ok:
        return (
            "pass",
            "partial",
            True,
            False,
            "D5 链路已跑通，但主题数量或分组质量仍需校准。",
        )
    return (
        "partial",
        "fail",
        False,
        False,
        "D5 未生成可用需求主题，请检查 D4 输入数据。",
    )


def _theme_summary_row(theme: Any) -> dict[str, Any]:
    return {
        "theme_id": theme.theme_id,
        "theme_title_zh": theme.theme_title_zh,
        "core_pain_zh": theme.core_pain_zh,
        "persona_group": theme.persona_group,
        "workflow_group": theme.workflow_group,
        "evidence_count": theme.evidence_count,
        "unique_domain_count": theme.unique_domain_count,
        "first_hand_evidence_count": theme.first_hand_evidence_count,
        "reviewed_pursue_count": theme.reviewed_pursue_count,
        "commercial_potential": theme.commercial_potential,
        "action_recommendation": theme.action_recommendation,
        "representative_quotes": theme.representative_quotes,
        "representative_source_urls": theme.representative_source_urls,
        "recommendation_reason_zh": theme.recommendation_reason_zh,
    }


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def _merge_run_summary(payload: dict[str, Any], path: Path = Path("outputs/run_summary.json")) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, Any] = {}
    if path.exists() and path.read_text(encoding="utf-8").strip():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}
    existing.update(payload)
    path.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
