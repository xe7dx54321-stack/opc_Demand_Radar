"""Group deduped D4 pain items into D5 demand themes."""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from demand_radar.d5.d4_review_loader import build_review_lookup
from demand_radar.d5.d4_pain_loader import load_all_d4_pain_items
from demand_radar.d5.io_utils import input_path, load_config, output_path, read_jsonl, write_jsonl
from demand_radar.d5.theme_labeler import label_theme
from demand_radar.d5.theme_schema import DemandTheme
from demand_radar.state.raw_store import next_ids, utc_now_iso


def build_demand_themes(
    config_path: Path | str | None = None,
    deduped_path: Path | str | None = None,
    source_groups_path: Path | str | None = None,
    reviews_path: Path | str | None = None,
    output_path_value: Path | str | None = None,
    report_path: Path | str | None = None,
    llm_client: Any | None = None,
) -> list[DemandTheme]:
    cfg = load_config(config_path)
    deduped_items_path = deduped_path or output_path(
        cfg,
        "deduped_pain_items_path",
        "data/processed/d5/deduped_pain_items.jsonl",
    )
    source_groups_file = source_groups_path or output_path(
        cfg,
        "source_groups_path",
        "data/processed/d5/source_groups.jsonl",
    )
    review_path = reviews_path or input_path(
        cfg,
        "d4_reviews_path",
        "data/processed/reviews/d4_pain_signal_reviews.jsonl",
    )
    deduped_items = read_jsonl(deduped_items_path)
    source_groups = read_jsonl(source_groups_file)
    review_lookup = build_review_lookup(review_path)

    representative_items = [item for item in deduped_items if item.get("is_representative")]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    source_group_index = {row.get("representative_item_id"): row for row in source_groups}

    for item in representative_items:
        key = canonical_workflow_group(item)
        grouped[key].append(
            {
                "item": item,
                "source_group": source_group_index.get(item.get("pain_item_id")),
            }
        )

    theme_ids = next_ids("theme", [], len(grouped))
    themes: list[DemandTheme] = []
    for idx, (workflow_group, rows) in enumerate(grouped.items()):
        selected_rows = _collapse_same_domain(rows)
        evidence_items = [row["item"] for row in selected_rows]
        source_groups_for_theme = [row["source_group"] or {} for row in selected_rows]
        labels = label_theme(
            workflow_group,
            evidence_items=evidence_items,
            source_groups=source_groups_for_theme,
            review_lookup=review_lookup,
            llm_client=llm_client,
        )
        theme = DemandTheme(
            theme_id=theme_ids[idx],
            theme_title_zh=labels["theme_title_zh"],
            persona_group=labels["persona_group"],
            workflow_group=labels["workflow_group"],
            pain_type_group=labels["pain_type_group"],
            core_pain_zh=labels["core_pain_zh"],
            job_to_be_done_zh=labels["job_to_be_done_zh"],
            current_workaround_zh=labels["current_workaround_zh"],
            deduped_item_ids=[str(item.get("deduped_item_id") or item.get("pain_item_id")) for item in evidence_items],
            source_group_ids=[str(row["source_group"].get("source_group_id")) for row in selected_rows if row.get("source_group")],
            evidence_count=len(evidence_items),
            unique_source_url_count=len({str((row.get("source_group") or {}).get("source_url") or "") for row in selected_rows if row.get("source_group")}),
            unique_domain_count=len({str((row.get("source_group") or {}).get("result_domain") or "") for row in selected_rows if row.get("source_group")}),
            strong_count=sum(1 for item in evidence_items if str(item.get("evidence_strength") or "") == "strong"),
            medium_count=sum(1 for item in evidence_items if str(item.get("evidence_strength") or "") == "medium"),
            weak_count=sum(1 for item in evidence_items if str(item.get("evidence_strength") or "") == "weak"),
            first_hand_evidence_count=labels["first_hand_evidence_count"],
            workaround_evidence_count=labels["workaround_evidence_count"],
            marketing_or_vendor_evidence_count=labels["marketing_or_vendor_evidence_count"],
            job_description_evidence_count=labels["job_description_evidence_count"],
            reviewed_positive_count=labels["reviewed_positive_count"],
            reviewed_pursue_count=labels["reviewed_pursue_count"],
            reviewed_watch_count=labels["reviewed_watch_count"],
            reviewed_needs_more_evidence_count=labels["reviewed_needs_more_evidence_count"],
            reviewed_reject_count=labels["reviewed_reject_count"],
            commercial_potential=labels["commercial_potential"],
            evidence_quality=labels["evidence_quality"],
            source_diversity=labels["source_diversity"],
            confidence=labels["confidence"],
            action_recommendation=labels["action_recommendation"],
            recommendation_reason_zh=labels["recommendation_reason_zh"],
            representative_quotes=labels["representative_quotes"],
            representative_source_urls=labels["representative_source_urls"],
            created_at=utc_now_iso(),
            metadata={
                "workflow_group": workflow_group,
                "collapsed_domain_count": len(selected_rows),
                "review_lookup_size": len(review_lookup),
            },
        )
        themes.append(theme)

    themes.sort(key=_theme_sort_key)

    out_path = Path(output_path_value) if output_path_value else output_path(
        cfg,
        "demand_themes_path",
        "data/processed/d5/demand_themes.jsonl",
    )
    report_out = Path(report_path) if report_path else output_path(
        cfg,
        "demand_theme_report_path",
        "outputs/d5/demand_theme_report.md",
    )
    write_jsonl(out_path, themes)
    _write_report(themes, report_out)
    return themes


def canonical_workflow_group(item: dict[str, Any]) -> str:
    text = " ".join(
        str(item.get(key) or "")
        for key in ("workflow_stage", "pain_type", "job_to_be_done", "pain_description_zh", "title")
    ).lower()
    if any(term in text for term in ["deal sourcing", "deal flow", "pipeline management", "initial screening", "target identification"]):
        return "项目来源与筛选"
    if any(term in text for term in ["market research", "competitive analysis", "startup scouting", "market intelligence"]):
        return "市场研究与竞争分析"
    if any(term in text for term in ["research report", "memo", "report generation", "coverage scaling", "financial modeling", "earnings research", "data collection", "research execution"]):
        return "投研研究工作流自动化"
    if any(term in text for term in ["fragmentation", "information overload", "scattered", "multi-tool", "research management"]):
        return "投研工作流碎片化"
    if any(term in text for term in ["monitoring", "tracking", "portfolio"]):
        return "组合监控与持续跟踪"
    return "投研研究工作流自动化"


def _collapse_same_domain(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best_by_domain: dict[str, dict[str, Any]] = {}
    for row in rows:
        source_group = row.get("source_group") or {}
        domain = str(source_group.get("result_domain") or "unknown")
        existing = best_by_domain.get(domain)
        if existing is None or _evidence_score(row["item"]) > _evidence_score(existing["item"]):
            best_by_domain[domain] = row
    return list(best_by_domain.values())


def _evidence_score(item: dict[str, Any]) -> tuple[float, float, int]:
    strength_score = {"strong": 3.0, "medium": 2.0, "weak": 1.0}.get(str(item.get("evidence_strength") or ""), 0)
    review_score = {
        "reviewed_positive": 1.5,
        "reviewed_needs_more_evidence": 1.0,
        "reviewed_reject": -1.0,
        "unknown": 0.2,
        "unreviewed": 0.0,
    }.get(str(item.get("human_review_status") or "unreviewed"), 0)
    quote_len = len(str(item.get("evidence_quote") or ""))
    return (strength_score + review_score, float(item.get("confidence") or 0), quote_len)


def _theme_sort_key(theme: DemandTheme) -> tuple[int, float, int, int, str]:
    rank = {"pursue_candidate": 0, "watch": 1, "needs_more_evidence": 2, "reject": 3}.get(
        theme.action_recommendation,
        9,
    )
    return (
        rank,
        -float(theme.confidence or 0),
        -int(theme.first_hand_evidence_count or 0),
        -int(theme.reviewed_pursue_count or 0),
        str(theme.theme_title_zh or ""),
    )


def _write_report(themes: list[DemandTheme], report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# D5 Demand Theme Report",
        "",
        f"- theme_count: {len(themes)}",
        f"- pursue_candidate_count: {sum(1 for theme in themes if theme.action_recommendation == 'pursue_candidate')}",
        f"- watch_count: {sum(1 for theme in themes if theme.action_recommendation == 'watch')}",
        f"- needs_more_evidence_count: {sum(1 for theme in themes if theme.action_recommendation == 'needs_more_evidence')}",
        f"- reject_count: {sum(1 for theme in themes if theme.action_recommendation == 'reject')}",
        "",
    ]
    for theme in themes:
        lines.extend(
            [
                f"## {theme.theme_title_zh}",
                f"- theme_id: {theme.theme_id}",
                f"- core_pain_zh: {theme.core_pain_zh}",
                f"- persona_group: {theme.persona_group or 'n/a'}",
                f"- workflow_group: {theme.workflow_group or 'n/a'}",
                f"- pain_type_group: {theme.pain_type_group or 'n/a'}",
                f"- evidence_count: {theme.evidence_count}",
                f"- unique_domain_count: {theme.unique_domain_count}",
                f"- first_hand_evidence_count: {theme.first_hand_evidence_count}",
                f"- reviewed_pursue_count: {theme.reviewed_pursue_count}",
                f"- commercial_potential: {theme.commercial_potential}",
                f"- action_recommendation: {theme.action_recommendation}",
                f"- representative_source_urls: {', '.join(theme.representative_source_urls) if theme.representative_source_urls else 'n/a'}",
                "",
                f"证据摘要：{theme.recommendation_reason_zh}",
                "",
            ]
        )
    if not themes:
        lines.append("No themes generated.")
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
