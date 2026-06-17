"""Diagnose why MVP-D expansion candidates were rejected."""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from demand_radar.mvp_d2.reject_diagnostics_schema import RejectDiagnosticItem
from demand_radar.mvp_d2.utils import load_yaml_section, read_jsonl, truncate, write_jsonl
from demand_radar.state.raw_store import next_ids, utc_now_iso

DEFAULT_CONFIG_PATH = Path("configs/expansion_diagnostics_config.yaml")


def run_reject_diagnostics(
    config_path: Path | None = None,
    candidates_path: Path | None = None,
    pain_items_path: Path | None = None,
    seed_profiles_path: Path | None = None,
    query_plan_path: Path | None = None,
    output_path: Path | None = None,
    report_path: Path | None = None,
) -> tuple[list[RejectDiagnosticItem], dict[str, Any]]:
    cfg = load_yaml_section(config_path or DEFAULT_CONFIG_PATH, "expansion_diagnostics")
    input_cfg = cfg.get("input", {})
    output_cfg = cfg.get("output", {})
    bucket_cfg = cfg.get("buckets", {})

    candidate_rows = read_jsonl(
        candidates_path or input_cfg.get("expansion_candidates_path", "data/processed/mvp_d/expansion_evidence_candidates.jsonl")
    )
    pain_rows = read_jsonl(
        pain_items_path or input_cfg.get("expansion_pain_items_path", "data/processed/mvp_d/expansion_pain_items.jsonl")
    )
    seed_rows = read_jsonl(
        seed_profiles_path or input_cfg.get("seed_profiles_path", "data/processed/mvp_d/seed_profiles.jsonl")
    )
    query_rows = read_jsonl(
        query_plan_path or input_cfg.get("query_plan_path", "data/processed/mvp_d/seeded_query_plan.jsonl")
    )

    candidate_by_id = {row.get("candidate_id"): row for row in candidate_rows}
    seed_by_id = {row.get("seed_id"): row for row in seed_rows}
    query_by_id = {row.get("query_id"): row for row in query_rows}
    rejected_rows = [row for row in pain_rows if row.get("should_extract") is not True]

    ids = next_ids("reject_diag", [], len(rejected_rows))
    diagnostics: list[RejectDiagnosticItem] = []
    thin_chars = int(bucket_cfg.get("raw_text_too_thin_chars", 300))
    rich_chars = int(bucket_cfg.get("raw_text_good_chars", 1200))

    for index, pain in enumerate(rejected_rows):
        candidate = candidate_by_id.get(pain.get("candidate_id"), {})
        candidate_meta = candidate.get("metadata") or {}
        pain_meta = pain.get("metadata") or {}
        seed_id = candidate_meta.get("seed_id") or pain_meta.get("seed_id")
        query_id = candidate_meta.get("seed_query_id") or pain_meta.get("seed_query_id")
        query = query_by_id.get(query_id, {})
        seed = seed_by_id.get(seed_id, {})
        raw_text = candidate.get("raw_text") or ""
        raw_chars = len(raw_text.strip())
        raw_quality = bucket_raw_text(raw_chars, thin_chars=thin_chars, rich_chars=rich_chars)
        reject_reason = str(pain.get("reject_reason") or "")
        category = map_reject_category(
            reject_reason=reject_reason,
            candidate=candidate,
            query=query,
            raw_text_quality=raw_quality,
        )
        source_quality = classify_source_quality(candidate, category)
        usefulness = classify_candidate_usefulness(candidate, category, reject_reason)
        note = build_diagnostic_note_zh(
            candidate=candidate,
            query=query,
            seed=seed,
            category=category,
            raw_quality=raw_quality,
        )
        diagnostics.append(
            RejectDiagnosticItem(
                diagnostic_id=ids[index],
                candidate_id=str(pain.get("candidate_id") or candidate.get("candidate_id") or ""),
                seed_id=seed_id,
                pain_item_id=candidate_meta.get("pain_item_id") or pain_meta.get("pain_item_id") or seed.get("pain_item_id"),
                query_id=query_id,
                query=query.get("query"),
                query_type=query.get("query_type"),
                title=candidate.get("title") or pain.get("title"),
                source_url=candidate.get("source_url") or pain.get("source_url"),
                source_type=candidate.get("source_type") or pain.get("source_type"),
                connector=query.get("connector") or candidate_meta.get("expansion_source"),
                raw_text_chars=raw_chars,
                raw_text_quality=raw_quality,
                llm_should_extract=bool(pain.get("should_extract")),
                llm_reject_reason=reject_reason or None,
                reject_category=category,
                source_quality=source_quality,
                candidate_usefulness=usefulness,
                diagnostic_note_zh=note,
                created_at=utc_now_iso(),
                metadata={
                    "title_excerpt": truncate(candidate.get("title"), 120),
                    "raw_text_excerpt": truncate(raw_text, 300),
                    "source_name": candidate.get("source_name"),
                    "collection_query": candidate.get("collection_query"),
                    "seed_title": seed.get("title"),
                },
            )
        )

    out_path = Path(output_path or output_cfg.get("reject_diagnostics_path", "data/processed/mvp_d2/reject_diagnostics.jsonl"))
    write_jsonl(out_path, diagnostics)
    summary = summarize_diagnostics(diagnostics, len(pain_rows), len(candidate_rows))
    build_reject_diagnostics_report(
        diagnostics,
        summary,
        Path(report_path or output_cfg.get("reject_diagnostics_report_path", "outputs/mvp_d2/reject_diagnostics_report.md")),
    )
    return diagnostics, summary


def bucket_raw_text(raw_text_chars: int, thin_chars: int = 300, rich_chars: int = 1200) -> str:
    if raw_text_chars < thin_chars:
        return "too_thin"
    if raw_text_chars >= rich_chars:
        return "rich"
    return "adequate"


def map_reject_category(
    reject_reason: str,
    candidate: dict[str, Any] | None = None,
    query: dict[str, Any] | None = None,
    raw_text_quality: str = "adequate",
) -> str:
    candidate = candidate or {}
    query = query or {}
    reason = reject_reason.lower()
    title = str(candidate.get("title") or "").lower()
    raw = str(candidate.get("raw_text") or "").lower()
    combined = f"{title}\n{raw[:4000]}"
    source_type = str(candidate.get("source_type") or "").lower()
    query_text = str(query.get("query") or candidate.get("collection_query") or "").lower()

    if raw_text_quality == "too_thin":
        return "raw_text_too_thin"
    if "duplicate" in reason:
        return "duplicate_or_near_duplicate"
    if "domain relevance excluded" in reason or "score too low" in reason:
        if _looks_like_product_marketing(combined):
            return "product_marketing"
        if _looks_like_generic_article(combined):
            return "generic_article"
        if source_type == "github_issue" and _looks_like_technical_issue(combined):
            return "technical_issue_not_business_pain"
        return "domain_out"
    if "no persona" in reason or "persona" in reason:
        return "no_user_persona"
    if "workflow" in reason and ("missing" in reason or "no " in reason):
        return "no_workflow"
    if "no pain" in reason or "pain" in reason and "missing" in reason:
        return "no_pain"
    if "quote" in reason:
        return "no_evidence_quote"
    if _looks_like_product_marketing(combined):
        return "product_marketing"
    if _looks_like_generic_article(combined):
        return "generic_article"
    if source_type == "github_issue" and _looks_like_technical_issue(combined):
        return "technical_issue_not_business_pain"
    if "tool" in query_text and not any(term in query_text for term in ["pain", "manual", "spreadsheet", "frustrated", "problem"]):
        return "source_low_quality"
    return "unknown"


def classify_source_quality(candidate: dict[str, Any], category: str) -> str:
    source_type = str(candidate.get("source_type") or "").lower()
    if category in {"raw_text_too_thin", "source_low_quality"}:
        return "low"
    if category in {"generic_article", "product_marketing", "domain_out"}:
        return "low" if source_type in {"rss", "github_issue"} else "medium"
    if category == "technical_issue_not_business_pain":
        return "medium" if source_type == "github_issue" else "low"
    return "medium"


def classify_candidate_usefulness(candidate: dict[str, Any], category: str, reject_reason: str) -> str:
    text = f"{candidate.get('title') or ''}\n{candidate.get('raw_text') or ''}".lower()
    if category in {"product_marketing"}:
        return "useful_for_competitor_map"
    if category in {"generic_article", "technical_issue_not_business_pain"}:
        return "useful_for_market_context"
    if category in {"no_user_persona", "no_workflow", "no_pain", "no_evidence_quote", "prompt_too_strict_possible"}:
        return "useful_for_demand"
    if "alternative" in text or "competitor" in text or "pricing" in text:
        return "useful_for_competitor_map"
    return "not_useful"


def build_diagnostic_note_zh(
    candidate: dict[str, Any],
    query: dict[str, Any],
    seed: dict[str, Any],
    category: str,
    raw_quality: str,
) -> str:
    query_text = query.get("query") or candidate.get("collection_query") or "未知 query"
    source_type = candidate.get("source_type") or "unknown"
    seed_id = seed.get("seed_id") or (candidate.get("metadata") or {}).get("seed_id") or "unknown"
    category_note = {
        "domain_out": "候选内容与投资研究工作流相关性不足，LLM 域相关评分过低。",
        "product_marketing": "候选更像产品宣传或工具介绍，缺少真实用户痛点。",
        "technical_issue_not_business_pain": "候选主要是技术 issue 或工程任务，不是投资研究业务痛点。",
        "generic_article": "候选更像泛资讯/摘要内容，缺少具体用户、工作流和痛点证据。",
        "raw_text_too_thin": "候选原文过短，无法支撑痛点抽取。",
        "source_low_quality": "当前 source/query 组合噪音较高。",
        "unknown": "拒绝原因需要人工进一步归因。",
    }.get(category, "候选缺少抽取所需的关键证据字段。")
    return (
        f"来自 {seed_id} 的查询「{query_text}」在 {source_type} 上命中该候选，"
        f"raw_text 质量为 {raw_quality}。{category_note}"
    )


def summarize_diagnostics(
    diagnostics: list[RejectDiagnosticItem],
    total_pain_items: int,
    total_candidates: int,
) -> dict[str, Any]:
    by_seed = Counter(item.seed_id or "unknown" for item in diagnostics)
    by_query_type = Counter(item.query_type or "unknown" for item in diagnostics)
    by_source_type = Counter(item.source_type or "unknown" for item in diagnostics)
    by_category = Counter(item.reject_category for item in diagnostics)
    by_raw = Counter(item.raw_text_quality for item in diagnostics)
    by_usefulness = Counter(item.candidate_usefulness for item in diagnostics)
    by_source_quality = Counter(item.source_quality for item in diagnostics)
    by_query = Counter(item.query or "unknown" for item in diagnostics)
    promising_categories = {"no_user_persona", "no_workflow", "no_pain", "no_evidence_quote", "prompt_too_strict_possible"}
    promising_queries = Counter(
        item.query or "unknown"
        for item in diagnostics
        if item.reject_category in promising_categories or item.candidate_usefulness == "useful_for_demand"
    )
    return {
        "total_candidates": total_candidates,
        "total_pain_items": total_pain_items,
        "total_rejected": len(diagnostics),
        "by_seed": dict(by_seed),
        "by_query_type": dict(by_query_type),
        "by_source_type": dict(by_source_type),
        "by_reject_category": dict(by_category),
        "by_raw_text_quality": dict(by_raw),
        "by_candidate_usefulness": dict(by_usefulness),
        "source_quality_distribution": dict(by_source_quality),
        "top_bad_queries": by_query.most_common(10),
        "top_promising_queries": promising_queries.most_common(10),
        "top_failure_patterns": [
            f"{category}: {count}"
            for category, count in by_category.most_common(5)
        ],
    }


def build_reject_diagnostics_report(
    diagnostics: list[RejectDiagnosticItem],
    summary: dict[str, Any],
    report_path: Path = Path("outputs/mvp_d2/reject_diagnostics_report.md"),
) -> Path:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# MVP-D2 Reject Diagnostics Report",
        "",
        "## Summary",
        f"- total_rejected: {summary['total_rejected']}",
        f"- total_candidates: {summary['total_candidates']}",
        f"- by_seed: {json.dumps(summary['by_seed'], ensure_ascii=False)}",
        f"- by_query_type: {json.dumps(summary['by_query_type'], ensure_ascii=False)}",
        f"- by_source_type: {json.dumps(summary['by_source_type'], ensure_ascii=False)}",
        f"- by_reject_category: {json.dumps(summary['by_reject_category'], ensure_ascii=False)}",
        f"- by_raw_text_quality: {json.dumps(summary['by_raw_text_quality'], ensure_ascii=False)}",
        f"- by_candidate_usefulness: {json.dumps(summary['by_candidate_usefulness'], ensure_ascii=False)}",
        f"- source_quality_distribution: {json.dumps(summary['source_quality_distribution'], ensure_ascii=False)}",
        "",
        "## Top Bad Queries",
    ]
    for query, count in summary["top_bad_queries"]:
        lines.append(f"- {query}: {count}")
    lines.extend(["", "## Top Promising Queries"])
    if summary["top_promising_queries"]:
        for query, count in summary["top_promising_queries"]:
            lines.append(f"- {query}: {count}")
    else:
        lines.append("- none")
    lines.extend(["", "## Diagnostics"])
    for item in diagnostics[:80]:
        lines.extend(
            [
                f"### {item.diagnostic_id}",
                f"- candidate_id: {item.candidate_id}",
                f"- seed_id: {item.seed_id or 'n/a'}",
                f"- query_id: {item.query_id or 'n/a'}",
                f"- query: {item.query or 'n/a'}",
                f"- query_type: {item.query_type or 'n/a'}",
                f"- source_type: {item.source_type or 'n/a'}",
                f"- connector: {item.connector or 'n/a'}",
                f"- raw_text_chars: {item.raw_text_chars}",
                f"- raw_text_quality: {item.raw_text_quality}",
                f"- reject_category: {item.reject_category}",
                f"- source_quality: {item.source_quality}",
                f"- candidate_usefulness: {item.candidate_usefulness}",
                f"- llm_reject_reason: {item.llm_reject_reason or 'n/a'}",
                f"- note: {item.diagnostic_note_zh}",
                f"- title: {item.title or 'n/a'}",
                f"- source_url: {item.source_url or 'n/a'}",
                "",
            ]
        )
    if not diagnostics:
        lines.append("No rejected expansion candidates found.")
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return report_path


def _looks_like_technical_issue(text: str) -> bool:
    technical_terms = [
        "stack trace",
        "runtime",
        "api",
        "build",
        "ci",
        "pytest",
        "metadata",
        "schema",
        "worker",
        "provider",
        "repo",
        "pull request",
        "issue",
        "bug",
        "fix",
        "implementation",
        "architecture",
        "headless testing",
        "etl",
    ]
    return sum(1 for term in technical_terms if term in text) >= 2


def _looks_like_product_marketing(text: str) -> bool:
    marketing_terms = [
        "launch",
        "pricing",
        "sign up",
        "book a demo",
        "try it",
        "platform",
        "solution",
        "features",
        "customers",
        "product",
        "software",
    ]
    if "no user pain" in text:
        return True
    return sum(1 for term in marketing_terms if term in text) >= 4


def _looks_like_generic_article(text: str) -> bool:
    article_terms = [
        "daily content summary",
        "digest",
        "newsletter",
        "executive summary",
        "key insights",
        "article",
        "news",
        "report",
        "generated",
        "covered",
    ]
    return sum(1 for term in article_terms if term in text) >= 2
