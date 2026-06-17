"""Reports for D5 evidence consolidation and demand themes."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from demand_radar.d5.theme_schema import D5RunSummary


def build_d5_summary_report(
    summary: D5RunSummary,
    report_path: Path = Path("outputs/d5/d5_summary_report.md"),
    metadata: dict[str, Any] | None = None,
) -> Path:
    meta = metadata or {}
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# D5 Evidence Consolidation & Demand Theme Grouping Summary",
        "",
        "## Run Metadata",
        f"- generated_at: {summary.generated_at}",
        f"- radar_commit: {summary.radar_commit}",
        f"- input_pain_items_path: {summary.input_pain_items_path}",
        f"- input_reviews_path: {summary.input_reviews_path}",
        "",
        "## Input Summary",
        f"- total_d4_pain_items: {summary.total_d4_pain_items}",
        f"- should_extract_true: {summary.should_extract_true}",
        f"- strong: {summary.strong}",
        f"- medium: {summary.medium}",
        f"- weak: {summary.weak}",
        f"- reviewed_count: {summary.reviewed_count}",
        f"- reviewed_pursue: {summary.reviewed_pursue}",
        f"- reviewed_needs_more_evidence: {summary.reviewed_needs_more_evidence}",
        f"- reviewed_reject: {summary.reviewed_reject}",
        "",
        "## Dedupe Summary",
        f"- original_items: {summary.original_items}",
        f"- deduped_representatives: {summary.deduped_representatives}",
        f"- duplicate_groups: {summary.duplicate_groups}",
        f"- top_duplicate_domains: {json.dumps(meta.get('top_duplicate_domains', {}), ensure_ascii=False)}",
        f"- top_duplicate_urls: {json.dumps(meta.get('top_duplicate_urls', {}), ensure_ascii=False)}",
        "",
        "## Source Quality Summary",
        f"- first_hand_community: {meta.get('first_hand_community', 0)}",
        f"- workaround_discussion: {meta.get('workaround_discussion', 0)}",
        f"- practitioner_blog: {meta.get('practitioner_blog', 0)}",
        f"- vendor_blog: {meta.get('vendor_blog', 0)}",
        f"- content_marketing: {meta.get('content_marketing', 0)}",
        f"- job_description: {meta.get('job_description', 0)}",
        f"- generic_article: {meta.get('generic_article', 0)}",
        f"- technical_issue: {meta.get('technical_issue', 0)}",
        "",
        "## Demand Themes",
    ]
    for theme in meta.get("themes", []):
        lines.extend(
            [
                f"### {theme['theme_title_zh']}",
                f"- theme_id: {theme['theme_id']}",
                f"- core_pain_zh: {theme['core_pain_zh']}",
                f"- persona_group: {theme['persona_group']}",
                f"- workflow_group: {theme['workflow_group']}",
                f"- evidence_count: {theme['evidence_count']}",
                f"- unique_domain_count: {theme['unique_domain_count']}",
                f"- first_hand_evidence_count: {theme['first_hand_evidence_count']}",
                f"- reviewed_pursue_count: {theme['reviewed_pursue_count']}",
                f"- commercial_potential: {theme['commercial_potential']}",
                f"- action_recommendation: {theme['action_recommendation']}",
                f"- representative_quotes: {json.dumps(theme['representative_quotes'], ensure_ascii=False)}",
                f"- representative_source_urls: {json.dumps(theme['representative_source_urls'], ensure_ascii=False)}",
                f"- recommendation_reason_zh: {theme['recommendation_reason_zh']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Theme Review Queue",
            f"- queue_count: {summary.queue_count}",
            f"- high_priority: {meta.get('high_priority', 0)}",
            f"- medium_priority: {meta.get('medium_priority', 0)}",
            f"- low_priority: {meta.get('low_priority', 0)}",
            "",
            "## Acceptance",
            f"- engineering_acceptance: {summary.engineering_acceptance}",
            f"- product_acceptance: {summary.product_acceptance}",
            f"- can_enter_theme_review: {str(summary.can_enter_theme_review).lower()}",
            f"- can_enter_product_discovery: {str(summary.can_enter_product_discovery).lower()}",
            f"- reason: {summary.reason}",
            "",
        ]
    )
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return report_path

