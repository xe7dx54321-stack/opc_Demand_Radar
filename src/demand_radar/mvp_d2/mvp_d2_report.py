"""Report builders for MVP-D2."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from demand_radar.mvp_d2.reject_diagnostics_schema import MVPD2RunSummary


def build_mvp_d2_summary_report(
    summary: MVPD2RunSummary,
    report_path: Path = Path("outputs/mvp_d2/mvp_d2_summary_report.md"),
) -> Path:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    meta = summary.metadata
    lines = [
        "# MVP-D2 Expansion Diagnostics & Query Calibration Summary",
        "",
        "## Run Metadata",
        f"- generated_at: {summary.generated_at}",
        f"- radar_commit: {summary.radar_commit}",
        f"- foundation_commit: {summary.foundation_commit}",
        f"- provider: {summary.provider}",
        f"- model: {summary.model}",
        f"- real_llm_run: {str(summary.real_llm_run).lower()}",
        f"- cache_enabled: {str(summary.cache_enabled).lower()}",
        "",
        "## Problem Statement",
        f"- MVP-D selected_for_llm: {summary.mvp_d_selected_for_llm}",
        f"- MVP-D should_extract_true: {summary.mvp_d_should_extract_true}",
        f"- MVP-D reject_count: {summary.mvp_d_reject_count}",
        "",
        "## Reject Diagnostics",
        f"- by_reject_category: {json.dumps(meta.get('by_reject_category', {}), ensure_ascii=False)}",
        f"- by_source_type: {json.dumps(meta.get('by_source_type', {}), ensure_ascii=False)}",
        f"- by_query_type: {json.dumps(meta.get('by_query_type', {}), ensure_ascii=False)}",
        f"- by_raw_text_quality: {json.dumps(meta.get('by_raw_text_quality', {}), ensure_ascii=False)}",
        f"- top_failure_patterns: {json.dumps(meta.get('top_failure_patterns', []), ensure_ascii=False)}",
        "",
        "## Source Strategy",
        f"- source_quality_scores: {json.dumps(meta.get('source_quality_scores', {}), ensure_ascii=False)}",
        f"- keep: {json.dumps(meta.get('keep', []), ensure_ascii=False)}",
        f"- deprioritize: {json.dumps(meta.get('deprioritize', []), ensure_ascii=False)}",
        f"- use_only_for_context: {json.dumps(meta.get('use_only_for_context', []), ensure_ascii=False)}",
        f"- needs_better_query: {json.dumps(meta.get('needs_better_query', []), ensure_ascii=False)}",
        f"- needs_new_connector: {json.dumps(meta.get('needs_new_connector', []), ensure_ascii=False)}",
        "",
        "## Query Calibration",
        f"- generated_v2_queries: {summary.generated_v2_queries}",
        f"- query_types: {json.dumps(meta.get('query_types', {}), ensure_ascii=False)}",
        f"- example_queries: {json.dumps(meta.get('example_queries', []), ensure_ascii=False)}",
        "",
        "## Calibrated Pilot",
        f"- ran_pilot: {str(summary.ran_pilot).lower()}",
        f"- blocked_reason: {summary.blocked_reason or 'n/a'}",
        f"- raw_new_signals: {summary.raw_new_signals}",
        f"- unique_new_signals: {summary.unique_new_signals}",
        f"- selected_for_llm: {summary.selected_for_llm}",
        f"- should_extract_true: {summary.should_extract_true}",
        f"- yield_rate: {summary.yield_rate}",
        "",
        "## Acceptance",
        f"- engineering_acceptance: {summary.engineering_acceptance}",
        f"- product_acceptance: {summary.product_acceptance}",
        f"- can_rerun_seeded_expansion: {str(summary.can_rerun_seeded_expansion).lower()}",
        f"- can_enter_second_review: {str(summary.can_enter_second_review).lower()}",
        f"- can_enter_foundation_source_upgrade: {str(summary.can_enter_foundation_source_upgrade).lower()}",
        f"- reason: {summary.reason}",
        "",
        "## Recommended Next Actions",
    ]
    actions = meta.get("recommended_next_actions") or [
        "用 calibrated query v2 重跑一轮 seeded expansion。",
        "如继续 blocked，先接入可验证的 search provider，再决定是否沉淀新 Foundation connector。",
        "优先人工抽查 v2 query 命中的候选质量，校准 source/category 权重。",
    ]
    for action in actions:
        lines.append(f"- {action}")
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return report_path
