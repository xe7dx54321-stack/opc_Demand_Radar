"""MVP-D summary report generation."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from demand_radar.mvp_d.seed_schema import MVPDRunSummary
from demand_radar.state.raw_store import utc_now_iso


def build_mvp_d_summary_report(
    summary: MVPDRunSummary,
    report_path: Path = Path("outputs/mvp_d/mvp_d_summary_report.md"),
    metadata: dict[str, Any] | None = None,
) -> Path:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    meta = metadata or {}
    lines = [
        "# MVP-D Seeded Evidence Expansion Summary",
        "",
        "## Run Metadata",
        f"- generated_at: {summary.generated_at}",
        f"- radar_commit: {meta.get('radar_commit', 'unknown')}",
        f"- foundation_commit: {meta.get('foundation_commit', 'unknown')}",
        f"- provider: {meta.get('provider', 'none')}",
        f"- model: {meta.get('model', 'none')}",
        f"- real_llm_run: {str(meta.get('real_llm_run', False)).lower()}",
        f"- cache_enabled: {str(meta.get('cache_enabled', True)).lower()}",
        "",
        "## Seed Summary",
        f"- total_reviews: {summary.total_reviews}",
        f"- eligible_seeds: {summary.eligible_seeds}",
        f"- optional_seeds: {summary.optional_seeds}",
        f"- excluded_reviews: {summary.excluded_reviews}",
        f"- selected_seed_ids: {json.dumps(meta.get('selected_seed_ids', []), ensure_ascii=False)}",
        "",
        "## Query Plan",
        f"- total_queries: {meta.get('total_queries', 0)}",
        f"- queries_by_seed: {json.dumps(meta.get('queries_by_seed', {}), ensure_ascii=False)}",
        f"- queries_by_connector: {json.dumps(meta.get('queries_by_connector', {}), ensure_ascii=False)}",
        f"- query_examples: {json.dumps(meta.get('query_examples', []), ensure_ascii=False)}",
        "",
        "## Acquisition Results",
        f"- raw_new_signals: {summary.raw_new_signals}",
        f"- unique_new_signals: {summary.unique_new_signals}",
        f"- deduped_against_existing: {summary.deduped_against_existing}",
        f"- allowed_by_real_signal_gate: {summary.allowed_by_gate}",
        f"- blocked_by_real_signal_gate: {summary.blocked_by_gate}",
        f"- source_url_present: {meta.get('source_url_present', 0)}",
        "",
        "## Extraction Results",
        f"- selected_for_llm: {summary.selected_for_llm}",
        f"- should_extract_true: {summary.should_extract_true}",
        f"- strong: {meta.get('strong', 0)}",
        f"- medium: {meta.get('medium', 0)}",
        f"- weak: {meta.get('weak', 0)}",
        f"- reject: {summary.expansion_pain_items - summary.should_extract_true}",
        f"- failures: {meta.get('failures', 0)}",
        f"- cache_hits: {meta.get('cache_hits', 0)}",
        "",
        "## Evidence Consolidation",
        f"- seeds_with_new_support: {meta.get('seeds_with_new_support', 0)}",
        f"- seeds_without_new_support: {meta.get('seeds_without_new_support', 0)}",
        f"- pursue_candidate: {meta.get('pursue_candidate', 0)}",
        f"- watch: {meta.get('watch', 0)}",
        f"- needs_more_evidence: {meta.get('needs_more_evidence', 0)}",
        f"- reject: {meta.get('reject', 0)}",
        "",
        "## Demand Themes",
        f"- theme_count: {summary.themes}",
        f"- top_themes: {json.dumps(meta.get('top_themes', []), ensure_ascii=False)}",
        "",
        "## Acceptance",
        f"- engineering_acceptance: {summary.engineering_acceptance}",
        f"- product_acceptance: {summary.product_acceptance}",
        f"- can_enter_second_review: {str(summary.can_enter_second_review).lower()}",
        f"- can_enter_product_discovery: {str(summary.can_enter_product_discovery).lower()}",
        f"- reason: {summary.reason}",
        "",
    ]
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return report_path
