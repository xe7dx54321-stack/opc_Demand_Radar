"""Analyze MVP-D source quality for demand evidence discovery."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from demand_radar.mvp_d2.reject_diagnostics_runner import run_reject_diagnostics
from demand_radar.mvp_d2.reject_diagnostics_schema import RejectDiagnosticItem, SourceQualityScore
from demand_radar.mvp_d2.utils import load_yaml_section, read_jsonl, write_jsonl
from demand_radar.state.raw_store import next_ids, utc_now_iso

DEFAULT_CONFIG_PATH = Path("configs/expansion_diagnostics_config.yaml")


def analyze_source_quality(
    config_path: Path | None = None,
    diagnostics_path: Path | None = None,
    candidates_path: Path | None = None,
    pain_items_path: Path | None = None,
    output_path: Path | None = None,
    report_path: Path | None = None,
) -> tuple[list[SourceQualityScore], dict[str, Any]]:
    cfg = load_yaml_section(config_path or DEFAULT_CONFIG_PATH, "expansion_diagnostics")
    input_cfg = cfg.get("input", {})
    output_cfg = cfg.get("output", {})
    diag_path = Path(diagnostics_path or output_cfg.get("reject_diagnostics_path", "data/processed/mvp_d2/reject_diagnostics.jsonl"))
    if diag_path.exists():
        diagnostics = [RejectDiagnosticItem.model_validate(row) for row in read_jsonl(diag_path)]
    else:
        diagnostics, _ = run_reject_diagnostics(config_path=config_path)

    candidate_rows = read_jsonl(
        candidates_path or input_cfg.get("expansion_candidates_path", "data/processed/mvp_d/expansion_evidence_candidates.jsonl")
    )
    pain_rows = read_jsonl(
        pain_items_path or input_cfg.get("expansion_pain_items_path", "data/processed/mvp_d/expansion_pain_items.jsonl")
    )
    candidate_by_id = {row.get("candidate_id"): row for row in candidate_rows}
    pain_by_id = {row.get("candidate_id"): row for row in pain_rows}
    diagnostics_by_candidate = {item.candidate_id: item for item in diagnostics}

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidate_rows:
        source_type = str(candidate.get("source_type") or "unknown")
        connector = str((candidate.get("metadata") or {}).get("expansion_source") or source_type)
        grouped[(source_type, connector)].append(candidate)

    ids = next_ids("source_quality", [], len(grouped))
    scores: list[SourceQualityScore] = []
    for index, ((source_type, connector), candidates) in enumerate(sorted(grouped.items())):
        candidate_ids = {row.get("candidate_id") for row in candidates}
        processed = [pain_by_id[cid] for cid in candidate_ids if cid in pain_by_id]
        should_extract_true = sum(1 for row in processed if row.get("should_extract") is True)
        reject_count = sum(1 for row in processed if row.get("should_extract") is not True)
        categories = Counter(
            diagnostics_by_candidate[cid].reject_category
            for cid in candidate_ids
            if cid in diagnostics_by_candidate
        )
        dominant = categories.most_common(1)[0][0] if categories else None
        yield_rate = round(should_extract_true / len(processed), 4) if processed else 0.0
        recommendation = recommend_source_strategy(
            source_type=source_type,
            connector=connector,
            yield_rate=yield_rate,
            llm_processed=len(processed),
            reject_count=reject_count,
            dominant_reject_reason=dominant,
        )
        quality_score = source_quality_score(
            yield_rate=yield_rate,
            total_candidates=len(candidates),
            llm_processed=len(processed),
            dominant_reject_reason=dominant,
        )
        scores.append(
            SourceQualityScore(
                score_id=ids[index],
                source_type=source_type,
                connector=connector,
                total_candidates=len(candidates),
                gate_allowed=len(processed),
                llm_processed=len(processed),
                should_extract_true=should_extract_true,
                reject_count=reject_count,
                yield_rate=yield_rate,
                dominant_reject_reason=dominant,
                source_quality_score=quality_score,
                source_strategy_recommendation=recommendation,
                created_at=utc_now_iso(),
                metadata={
                    "reject_categories": dict(categories),
                    "example_candidate_ids": [str(cid) for cid in list(candidate_ids)[:5] if cid],
                },
            )
        )

    out_path = Path(output_path or output_cfg.get("source_quality_scores_path", "data/processed/mvp_d2/source_quality_scores.jsonl"))
    write_jsonl(out_path, scores)
    summary = summarize_source_quality(scores)
    build_source_quality_report(
        scores,
        summary,
        Path(report_path or output_cfg.get("source_quality_report_path", "outputs/mvp_d2/source_quality_report.md")),
    )
    return scores, summary


def recommend_source_strategy(
    source_type: str,
    connector: str,
    yield_rate: float,
    llm_processed: int,
    reject_count: int,
    dominant_reject_reason: str | None,
) -> str:
    stype = source_type.lower()
    dominant = dominant_reject_reason or "unknown"
    if yield_rate >= 0.20 and llm_processed > 0:
        return "keep"
    if stype == "github_issue" and reject_count >= llm_processed and llm_processed > 0:
        if dominant == "technical_issue_not_business_pain":
            return "use_only_for_context"
        return "needs_better_query"
    if stype == "rss":
        if dominant in {"generic_article", "domain_out"} or yield_rate == 0:
            return "deprioritize"
        return "needs_better_query"
    if stype in {"community_discussion", "hacker_news"}:
        return "needs_better_query" if yield_rate == 0 else "keep"
    if stype in {"manual_url", "web_page"}:
        return "needs_new_connector" if llm_processed == 0 else "needs_better_query"
    return "needs_new_connector" if llm_processed == 0 else "use_only_for_context"


def source_quality_score(
    yield_rate: float,
    total_candidates: int,
    llm_processed: int,
    dominant_reject_reason: str | None,
) -> float:
    score = yield_rate
    if llm_processed:
        score += 0.15
    if total_candidates:
        score += min(0.15, total_candidates / 100)
    if dominant_reject_reason in {"generic_article", "domain_out", "product_marketing"}:
        score -= 0.10
    if dominant_reject_reason == "technical_issue_not_business_pain":
        score -= 0.05
    return round(max(0.0, min(1.0, score)), 4)


def summarize_source_quality(scores: list[SourceQualityScore]) -> dict[str, Any]:
    by_recommendation = Counter(score.source_strategy_recommendation for score in scores)
    return {
        "source_quality_scores": {
            score.source_type: score.source_quality_score for score in scores
        },
        "keep": [score.source_type for score in scores if score.source_strategy_recommendation == "keep"],
        "deprioritize": [score.source_type for score in scores if score.source_strategy_recommendation == "deprioritize"],
        "use_only_for_context": [score.source_type for score in scores if score.source_strategy_recommendation == "use_only_for_context"],
        "needs_better_query": [score.source_type for score in scores if score.source_strategy_recommendation == "needs_better_query"],
        "needs_new_connector": [score.source_type for score in scores if score.source_strategy_recommendation == "needs_new_connector"],
        "by_recommendation": dict(by_recommendation),
        "key_findings": build_key_findings(scores),
    }


def build_key_findings(scores: list[SourceQualityScore]) -> list[str]:
    findings: list[str] = []
    for score in scores:
        if score.source_type == "github_issue" and score.yield_rate == 0:
            findings.append("GitHub Issues 在 v1 中没有产生新增痛点证据，更适合作为技术/市场上下文或需要更严格 query。")
        elif score.source_type == "rss" and score.yield_rate == 0:
            findings.append("RSS 在 v1 中偏泛资讯，作为 pain evidence source 应降权。")
        elif score.source_type == "community_discussion" and score.yield_rate == 0:
            findings.append("社区讨论数量太少但 source 类型仍值得保留，需要改用痛点/工作流 query。")
    if not findings:
        findings.append("当前 source mix 未显示稳定新增痛点证据，需要 query v2 或新 source 验证。")
    return findings


def build_source_quality_report(
    scores: list[SourceQualityScore],
    summary: dict[str, Any],
    report_path: Path = Path("outputs/mvp_d2/source_quality_report.md"),
) -> Path:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# MVP-D2 Source Quality Report",
        "",
        "## Summary",
        f"- source_quality_scores: {json.dumps(summary['source_quality_scores'], ensure_ascii=False)}",
        f"- keep: {json.dumps(summary['keep'], ensure_ascii=False)}",
        f"- deprioritize: {json.dumps(summary['deprioritize'], ensure_ascii=False)}",
        f"- use_only_for_context: {json.dumps(summary['use_only_for_context'], ensure_ascii=False)}",
        f"- needs_better_query: {json.dumps(summary['needs_better_query'], ensure_ascii=False)}",
        f"- needs_new_connector: {json.dumps(summary['needs_new_connector'], ensure_ascii=False)}",
        "",
        "## Key Findings",
    ]
    for finding in summary["key_findings"]:
        lines.append(f"- {finding}")
    lines.extend(
        [
            "",
            "## Scores",
            "",
            "| Source Type | Connector | Candidates | LLM Processed | Extracted | Yield | Dominant Reject | Score | Recommendation |",
            "|---|---|---:|---:|---:|---:|---|---:|---|",
        ]
    )
    for score in scores:
        lines.append(
            f"| {score.source_type} | {score.connector} | {score.total_candidates} | "
            f"{score.llm_processed} | {score.should_extract_true} | {score.yield_rate:.4f} | "
            f"{score.dominant_reject_reason or 'n/a'} | {score.source_quality_score:.4f} | "
            f"{score.source_strategy_recommendation} |"
        )
    if not scores:
        lines.append("No source quality rows generated.")
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return report_path
