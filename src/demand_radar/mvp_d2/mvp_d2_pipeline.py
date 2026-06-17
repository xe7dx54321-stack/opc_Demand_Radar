"""MVP-D2 end-to-end diagnostics and query calibration pipeline."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from demand_radar.mvp_d2.calibrated_expansion_runner import run_calibrated_expansion
from demand_radar.mvp_d2.calibrated_query_generator import build_calibrated_query_plan
from demand_radar.mvp_d2.d2_comparison import compare_expansion_v1_v2
from demand_radar.mvp_d2.mvp_d2_report import build_mvp_d2_summary_report
from demand_radar.mvp_d2.reject_diagnostics_runner import run_reject_diagnostics
from demand_radar.mvp_d2.reject_diagnostics_schema import MVPD2RunSummary
from demand_radar.mvp_d2.source_quality_analyzer import analyze_source_quality
from demand_radar.mvp_d2.utils import git_commit, read_markdown_kv
from demand_radar.state.raw_store import utc_now_iso


def run_mvp_d2(
    domain_id: str = "ai_investment_tracking",
    max_queries: int | None = None,
    max_results: int | None = None,
    use_cache: bool = True,
    skip_pilot: bool = False,
    llm_client=None,
) -> MVPD2RunSummary:
    diagnostics, diag_summary = run_reject_diagnostics()
    source_scores, source_summary = analyze_source_quality()
    queries = build_calibrated_query_plan(max_queries=max_queries)
    _, _, pilot_summary = run_calibrated_expansion(
        max_queries=max_queries,
        max_results=max_results,
        use_cache=use_cache,
        skip_pilot=skip_pilot,
        llm_client=llm_client,
    )
    comparison = compare_expansion_v1_v2()
    mvp_d_report = read_markdown_kv("outputs/mvp_d/expansion_pain_extraction_report.md")

    engineering_acceptance, product_acceptance, can_rerun, can_second_review, can_foundation_upgrade, reason = _acceptance(
        diag_summary=diag_summary,
        query_count=len(queries),
        pilot_summary=pilot_summary,
        comparison_result=comparison["result"],
    )

    query_type_counts = Counter(query.query_type for query in queries)
    summary = MVPD2RunSummary(
        domain_id=domain_id,
        generated_at=utc_now_iso(),
        radar_commit=git_commit(),
        foundation_commit="b6d23bc",
        provider=str(pilot_summary.get("provider", mvp_d_report.get("provider", "none"))),
        model=str(pilot_summary.get("model", mvp_d_report.get("model", "none"))),
        real_llm_run=bool(pilot_summary.get("real_llm_run", False)),
        cache_enabled=use_cache,
        mvp_d_selected_for_llm=int(mvp_d_report.get("selected_for_llm", 0)),
        mvp_d_should_extract_true=int(mvp_d_report.get("should_extract_true", 0)),
        mvp_d_reject_count=int(mvp_d_report.get("rejected", 0)),
        total_rejected=int(diag_summary.get("total_rejected", len(diagnostics))),
        generated_v2_queries=len(queries),
        ran_pilot=bool(pilot_summary.get("ran_pilot", False)),
        blocked_reason=pilot_summary.get("blocked_reason"),
        raw_new_signals=int(pilot_summary.get("raw_new_signals", 0)),
        unique_new_signals=int(pilot_summary.get("unique_new_signals", 0)),
        gate_allowed=int(pilot_summary.get("gate_allowed", 0)),
        selected_for_llm=int(pilot_summary.get("selected_for_llm", 0)),
        should_extract_true=int(pilot_summary.get("should_extract_true", 0)),
        yield_rate=float(pilot_summary.get("yield_rate", 0.0)),
        comparison_result=str(comparison["result"]),
        engineering_acceptance=engineering_acceptance,
        product_acceptance=product_acceptance,
        can_rerun_seeded_expansion=can_rerun,
        can_enter_second_review=can_second_review,
        can_enter_foundation_source_upgrade=can_foundation_upgrade,
        reason=reason,
        metadata={
            **diag_summary,
            **source_summary,
            "query_types": dict(query_type_counts),
            "example_queries": [query.query for query in queries[:10]],
            "pilot_summary": pilot_summary,
            "comparison": comparison,
            "recommended_next_actions": _recommended_actions(pilot_summary, comparison["result"], source_summary),
        },
    )
    build_mvp_d2_summary_report(summary)
    _merge_run_summary(
        {
            "mvp_d2_engineering_acceptance": summary.engineering_acceptance,
            "mvp_d2_product_acceptance": summary.product_acceptance,
            "mvp_d2_total_rejected": summary.total_rejected,
            "mvp_d2_generated_v2_queries": summary.generated_v2_queries,
            "mvp_d2_pilot_blocked_reason": summary.blocked_reason,
            "mvp_d2_comparison_result": summary.comparison_result,
            "mvp_d2_can_rerun_seeded_expansion": summary.can_rerun_seeded_expansion,
            "mvp_d2_can_enter_second_review": summary.can_enter_second_review,
            "mvp_d2_can_enter_foundation_source_upgrade": summary.can_enter_foundation_source_upgrade,
        }
    )
    return summary


def build_mvp_d2_summary_from_stored(
    domain_id: str = "ai_investment_tracking",
) -> MVPD2RunSummary:
    diagnostics, diag_summary = run_reject_diagnostics()
    _, source_summary = analyze_source_quality()
    queries = build_calibrated_query_plan()
    comparison = compare_expansion_v1_v2()
    pilot_summary = read_markdown_kv("outputs/mvp_d2/calibrated_expansion_report.md")
    mvp_d_report = read_markdown_kv("outputs/mvp_d/expansion_pain_extraction_report.md")
    engineering_acceptance, product_acceptance, can_rerun, can_second_review, can_foundation_upgrade, reason = _acceptance(
        diag_summary=diag_summary,
        query_count=len(queries),
        pilot_summary=pilot_summary,
        comparison_result=comparison["result"],
    )
    summary = MVPD2RunSummary(
        domain_id=domain_id,
        generated_at=utc_now_iso(),
        radar_commit=git_commit(),
        foundation_commit="b6d23bc",
        provider=str(pilot_summary.get("provider", "none")),
        model=str(pilot_summary.get("model", "none")),
        real_llm_run=bool(pilot_summary.get("real_llm_run", False)),
        cache_enabled=bool(pilot_summary.get("cache_enabled", True)),
        mvp_d_selected_for_llm=int(mvp_d_report.get("selected_for_llm", 0)),
        mvp_d_should_extract_true=int(mvp_d_report.get("should_extract_true", 0)),
        mvp_d_reject_count=int(mvp_d_report.get("rejected", 0)),
        total_rejected=int(diag_summary.get("total_rejected", len(diagnostics))),
        generated_v2_queries=len(queries),
        ran_pilot=bool(pilot_summary.get("ran_pilot", False)),
        blocked_reason=pilot_summary.get("blocked_reason") if pilot_summary.get("blocked_reason") != "n/a" else None,
        raw_new_signals=int(pilot_summary.get("raw_new_signals", 0)),
        unique_new_signals=int(pilot_summary.get("unique_new_signals", 0)),
        gate_allowed=int(pilot_summary.get("gate_allowed", 0)),
        selected_for_llm=int(pilot_summary.get("selected_for_llm", 0)),
        should_extract_true=int(pilot_summary.get("should_extract_true", 0)),
        yield_rate=float(pilot_summary.get("yield_rate", 0.0)),
        comparison_result=comparison["result"],
        engineering_acceptance=engineering_acceptance,
        product_acceptance=product_acceptance,
        can_rerun_seeded_expansion=can_rerun,
        can_enter_second_review=can_second_review,
        can_enter_foundation_source_upgrade=can_foundation_upgrade,
        reason=reason,
        metadata={
            **diag_summary,
            **source_summary,
            "query_types": dict(Counter(query.query_type for query in queries)),
            "example_queries": [query.query for query in queries[:10]],
            "pilot_summary": pilot_summary,
            "comparison": comparison,
            "recommended_next_actions": _recommended_actions(pilot_summary, comparison["result"], source_summary),
        },
    )
    build_mvp_d2_summary_report(summary)
    return summary


def _acceptance(
    diag_summary: dict[str, Any],
    query_count: int,
    pilot_summary: dict[str, Any],
    comparison_result: str,
) -> tuple[str, str, bool, bool, bool, str]:
    diagnostics_ok = int(diag_summary.get("total_rejected", 0)) > 0
    query_ok = query_count > 0
    pilot_blocked = pilot_summary.get("blocked_reason") in {"blocked_by_missing_search_provider", "pilot_skipped"} or pilot_summary.get("status") == "blocked"
    if diagnostics_ok and query_ok and pilot_blocked:
        return (
            "pass",
            "partial",
            True,
            False,
            True,
            "诊断和 query v2 已生成，但 calibrated pilot 因缺少 search provider 或被跳过而未完成真实验证。",
        )
    if diagnostics_ok and query_ok and comparison_result == "improved":
        can_second_review = int(pilot_summary.get("should_extract_true", 0)) > 0
        return (
            "pass",
            "pass" if can_second_review else "partial",
            True,
            can_second_review,
            False,
            "query v2 pilot yield 高于 v1，可进入下一轮 seeded expansion 或人工复核。",
        )
    if diagnostics_ok and query_ok:
        return (
            "pass",
            "partial",
            True,
            int(pilot_summary.get("should_extract_true", 0)) > 0,
            comparison_result == "blocked",
            "诊断和 query v2 可用，但 pilot 暂未证明新增痛点证据 yield 改善。",
        )
    return (
        "partial",
        "fail",
        False,
        False,
        False,
        "D2 诊断或 calibrated query plan 未达到工程验收。",
    )


def _recommended_actions(
    pilot_summary: dict[str, Any],
    comparison_result: str,
    source_summary: dict[str, Any],
) -> list[str]:
    actions: list[str] = []
    if pilot_summary.get("blocked_reason") == "blocked_by_missing_search_provider":
        actions.append("接入一个可验证的 search provider 做小批量 URL pilot，不要直接新增 Foundation connector。")
    if source_summary.get("needs_better_query"):
        actions.append("用 calibrated query v2 重跑 MVP-D seeded expansion，优先观察 community discussion 和 workaround 类命中。")
    if source_summary.get("deprioritize"):
        actions.append("降低 RSS 泛资讯在痛点证据发现中的优先级，仅用于市场上下文。")
    if comparison_result == "improved":
        actions.append("对 V2 命中的 should_extract=true 结果做第二轮人工 review。")
    if not actions:
        actions.append("继续校准 source/query 策略，再决定是否升级 Foundation source 能力。")
    return actions


def _merge_run_summary(payload: dict[str, Any], path: Path = Path("outputs/run_summary.json")) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, Any] = {}
    if path.exists() and path.read_text(encoding="utf-8").strip():
        existing = json.loads(path.read_text(encoding="utf-8"))
    existing.update(payload)
    path.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
