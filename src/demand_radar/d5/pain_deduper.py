"""Dedupe D4 pain items into representative source evidence."""
from __future__ import annotations

from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from demand_radar.d5.d4_pain_loader import load_d4_pain_items
from demand_radar.d5.io_utils import input_path, load_config, output_path, write_jsonl
from demand_radar.d5.source_classifier import classify_source, source_weight
from demand_radar.d5.theme_schema import DedupedPainItem, SourceEvidenceGroup
from demand_radar.state.raw_store import next_ids, utc_now_iso


def dedupe_pain_items(
    config_path: Path | str | None = None,
    pain_items_path: Path | str | None = None,
    reviews_path: Path | str | None = None,
    deduped_output_path: Path | str | None = None,
    source_groups_output_path: Path | str | None = None,
    report_path: Path | str | None = None,
) -> tuple[list[DedupedPainItem], list[SourceEvidenceGroup], dict[str, Any]]:
    cfg = load_config(config_path)
    pain_path = pain_items_path or input_path(
        cfg,
        "d4_pain_items_path",
        "data/processed/mvp_d4/foundation_search_pain_items.jsonl",
    )
    review_path = reviews_path or input_path(
        cfg,
        "d4_reviews_path",
        "data/processed/reviews/d4_pain_signal_reviews.jsonl",
    )
    include_strengths = set(
        cfg.get("evidence_selection", {}).get("include_strength", ["strong", "medium"])
    )
    items = load_d4_pain_items(
        path=pain_path,
        include_strengths=include_strengths,
        reviews_path=review_path,
    )

    grouped = _group_by_source_url(items)
    deduped_ids = next_ids("deduped_item", [], len(items))
    source_group_ids = next_ids("source_group", [], len(grouped))
    deduped_items: list[DedupedPainItem] = []
    source_groups: list[SourceEvidenceGroup] = []

    id_index = 0
    for group_index, (source_key, rows) in enumerate(grouped.items()):
        duplicate_group_id = source_group_ids[group_index]
        classified_rows = [_with_source_category(row) for row in rows]
        representative = _choose_representative(classified_rows)
        source_group = _build_source_group(
            source_group_id=duplicate_group_id,
            rows=classified_rows,
            representative_pain_item_id=str(representative.get("pain_item_id") or ""),
        )
        source_groups.append(source_group)
        for row in classified_rows:
            pain_item_id = str(row.get("pain_item_id") or "")
            is_representative = pain_item_id == source_group.representative_item_id
            deduped_items.append(
                _build_deduped_item(
                    row=row,
                    deduped_item_id=deduped_ids[id_index],
                    duplicate_group_id=duplicate_group_id,
                    duplicate_reason=_duplicate_reason(rows, row, is_representative),
                    is_representative=is_representative,
                )
            )
            id_index += 1

    # Mark obvious near-duplicate pain descriptions inside the same domain as related metadata.
    _annotate_domain_similarities(deduped_items)

    deduped_path = Path(deduped_output_path) if deduped_output_path else output_path(
        cfg,
        "deduped_pain_items_path",
        "data/processed/d5/deduped_pain_items.jsonl",
    )
    source_groups_path = Path(source_groups_output_path) if source_groups_output_path else output_path(
        cfg,
        "source_groups_path",
        "data/processed/d5/source_groups.jsonl",
    )
    write_jsonl(deduped_path, deduped_items)
    write_jsonl(source_groups_path, source_groups)

    summary = build_dedupe_summary(items, deduped_items, source_groups)
    _write_dedupe_report(
        summary,
        report_path=Path(report_path) if report_path else output_path(
            cfg,
            "dedupe_report_path",
            "outputs/d5/dedupe_report.md",
        ),
    )
    _write_source_group_report(
        source_groups,
        report_path=output_path(cfg, "source_group_report_path", "outputs/d5/source_group_report.md"),
    )
    return deduped_items, source_groups, summary


def build_dedupe_summary(
    original_items: list[dict[str, Any]],
    deduped_items: list[DedupedPainItem],
    source_groups: list[SourceEvidenceGroup],
) -> dict[str, Any]:
    representative_count = sum(1 for item in deduped_items if item.is_representative)
    duplicate_groups = sum(1 for group in source_groups if group.evidence_count > 1)
    domains = Counter(item.result_domain or "unknown" for item in deduped_items)
    urls = Counter(item.source_url or "unknown" for item in deduped_items)
    return {
        "original_pain_items": len(original_items),
        "deduped_representatives": representative_count,
        "duplicate_groups": duplicate_groups,
        "source_groups": len(source_groups),
        "top_duplicate_domains": dict(domains.most_common(10)),
        "top_duplicate_urls": dict(urls.most_common(10)),
    }


def _group_by_source_url(items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in items:
        key = str(row.get("source_url") or row.get("result_domain") or row.get("candidate_id") or "")
        groups[key].append(row)
    return dict(groups)


def _with_source_category(row: dict[str, Any]) -> dict[str, Any]:
    category, weight = classify_source(row)
    out = dict(row)
    out["source_category"] = category
    out["source_weight"] = weight
    return out


def _choose_representative(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return sorted(rows, key=_representative_score, reverse=True)[0]


def _representative_score(row: dict[str, Any]) -> tuple[float, float, int, str]:
    strength = {"strong": 3.0, "medium": 2.0, "weak": 1.0}.get(str(row.get("evidence_strength")), 0)
    reviewed = {
        "reviewed_positive": 1.5,
        "reviewed_needs_more_evidence": 1.0,
        "unknown": 0.5,
        "unreviewed": 0.0,
        "reviewed_reject": -2.0,
    }.get(str(row.get("human_review_status")), 0)
    category_weight = float(row.get("source_weight") or source_weight(row.get("source_category")))
    confidence = float(row.get("confidence") or 0)
    quote_len = len(str(row.get("evidence_quote") or ""))
    return (strength + reviewed + category_weight, confidence, quote_len, str(row.get("pain_item_id") or ""))


def _build_deduped_item(
    row: dict[str, Any],
    deduped_item_id: str,
    duplicate_group_id: str,
    duplicate_reason: str,
    is_representative: bool,
) -> DedupedPainItem:
    return DedupedPainItem(
        deduped_item_id=deduped_item_id,
        pain_item_id=str(row.get("pain_item_id") or ""),
        candidate_id=row.get("candidate_id"),
        title=row.get("title"),
        source_url=row.get("source_url"),
        result_domain=row.get("result_domain"),
        source_category=row.get("source_category"),
        persona=row.get("persona"),
        workflow_stage=row.get("workflow_stage"),
        pain_type=row.get("pain_type"),
        job_to_be_done=row.get("job_to_be_done"),
        pain_description_zh=row.get("pain_description_zh"),
        evidence_quote=row.get("evidence_quote"),
        evidence_strength=str(row.get("evidence_strength") or "weak"),
        confidence=float(row.get("confidence") or 0),
        commercial_signal_type=row.get("commercial_signal_type"),
        current_solution=row.get("current_solution"),
        raw_text_source=row.get("raw_text_source"),
        query_type=row.get("query_type"),
        seed_id=row.get("seed_id"),
        duplicate_group_id=duplicate_group_id,
        duplicate_reason=duplicate_reason,
        is_representative=is_representative,
        human_review_status=str(row.get("human_review_status") or "unreviewed"),
        human_action_decision=row.get("human_action_decision"),
        human_commercial_potential=row.get("human_commercial_potential"),
        created_at=utc_now_iso(),
        metadata={
            "source_weight": row.get("source_weight"),
            "human_true_pain": row.get("human_true_pain"),
            "human_evidence_quality": row.get("human_evidence_quality"),
            "human_extraction_quality": row.get("human_extraction_quality"),
            "original_should_extract": row.get("should_extract"),
        },
    )


def _build_source_group(
    source_group_id: str,
    rows: list[dict[str, Any]],
    representative_pain_item_id: str,
) -> SourceEvidenceGroup:
    representative = next((row for row in rows if row.get("pain_item_id") == representative_pain_item_id), rows[0])
    category = str(representative.get("source_category") or "unknown")
    strengths = Counter(str(row.get("evidence_strength") or "weak") for row in rows)
    reviewed_positive = sum(1 for row in rows if row.get("human_review_status") == "reviewed_positive")
    reviewed_reject = sum(1 for row in rows if row.get("human_review_status") == "reviewed_reject")
    summary = _source_summary(representative, rows)
    return SourceEvidenceGroup(
        source_group_id=source_group_id,
        source_url=representative.get("source_url"),
        result_domain=representative.get("result_domain"),
        item_ids=[str(row.get("pain_item_id") or "") for row in rows if row.get("pain_item_id")],
        representative_item_id=representative_pain_item_id,
        source_category=category,
        source_weight=source_weight(category),
        group_summary_zh=summary,
        evidence_count=len(rows),
        strong_count=strengths.get("strong", 0),
        medium_count=strengths.get("medium", 0),
        weak_count=strengths.get("weak", 0),
        reviewed_positive_count=reviewed_positive,
        reviewed_reject_count=reviewed_reject,
        created_at=utc_now_iso(),
        metadata={
            "all_pain_item_ids": [row.get("pain_item_id") for row in rows],
            "representative_selection_reason": "优先选择已人工正向审核、证据强度高、来源权重高、quote 更完整的条目。",
        },
    )


def _source_summary(representative: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    title = str(representative.get("title") or representative.get("result_domain") or "该来源")
    pain = str(representative.get("pain_description_zh") or "").strip()
    suffix = f"同源共 {len(rows)} 条 pain item，D5 仅将其作为 1 组来源证据计入主题。"
    if pain:
        return f"{title}：{pain[:180]}。{suffix}"
    return f"{title}：{suffix}"


def _duplicate_reason(rows: list[dict[str, Any]], row: dict[str, Any], is_representative: bool) -> str | None:
    if len(rows) <= 1:
        return None
    if is_representative:
        return "same_source_url_representative"
    return "same_source_url_duplicate"


def _annotate_domain_similarities(items: list[DedupedPainItem]) -> None:
    by_domain: dict[str, list[DedupedPainItem]] = defaultdict(list)
    for item in items:
        by_domain[item.result_domain or "unknown"].append(item)
    for domain_items in by_domain.values():
        reps = [item for item in domain_items if item.is_representative]
        for i, item in enumerate(reps):
            for other in reps[i + 1 :]:
                if _similarity(item.pain_description_zh, other.pain_description_zh) >= 0.82:
                    item.metadata["near_duplicate_within_domain"] = True
                    other.metadata["near_duplicate_within_domain"] = True


def _similarity(left: str | None, right: str | None) -> float:
    left = str(left or "").strip()
    right = str(right or "").strip()
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()


def _write_dedupe_report(summary: dict[str, Any], report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# D5 Dedupe Report",
        "",
        f"- original_pain_items: {summary['original_pain_items']}",
        f"- deduped_representatives: {summary['deduped_representatives']}",
        f"- duplicate_groups: {summary['duplicate_groups']}",
        f"- top_duplicate_domains: {summary['top_duplicate_domains']}",
        f"- top_duplicate_urls: {summary['top_duplicate_urls']}",
        "",
        "## Representative Selection",
        "同 source_url 的多条 pain item 只形成一个 source group，并优先选择人工正向审核、证据强度高、来源权重高、quote 更完整的代表项。",
        "非代表项保留在 deduped_pain_items.jsonl 中，但不会重复放大主题 evidence_count。",
        "",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")


def _write_source_group_report(source_groups: list[SourceEvidenceGroup], report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    category_counts = Counter(group.source_category for group in source_groups)
    lines = [
        "# D5 Source Group Report",
        "",
        f"- source_groups: {len(source_groups)}",
        f"- by_source_category: {dict(category_counts)}",
        "",
    ]
    for group in source_groups:
        lines.extend(
            [
                f"## {group.source_group_id}",
                f"- source_url: {group.source_url or 'n/a'}",
                f"- result_domain: {group.result_domain or 'n/a'}",
                f"- source_category: {group.source_category}",
                f"- source_weight: {group.source_weight}",
                f"- evidence_count: {group.evidence_count}",
                f"- strong_count: {group.strong_count}",
                f"- medium_count: {group.medium_count}",
                f"- reviewed_positive_count: {group.reviewed_positive_count}",
                "",
                group.group_summary_zh,
                "",
            ]
        )
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

