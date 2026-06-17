"""Run the MVP-D2 calibrated expansion pilot."""
from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path
from typing import Any

from demand_radar.mvp_d.expansion_extraction import run_expansion_extraction
from demand_radar.mvp_d.real_signal_gate import build_gate_report, run_gate
from demand_radar.mvp_d2.calibrated_query_generator import build_calibrated_query_plan
from demand_radar.mvp_d2.utils import load_dotenv, load_yaml_section, read_jsonl, write_jsonl
from demand_radar.state.raw_store import utc_now_iso

DEFAULT_CONFIG_PATH = Path("configs/query_calibration_config.yaml")


def run_calibrated_expansion(
    config_path: Path | None = None,
    query_plan_path: Path | None = None,
    candidates_path: Path | None = None,
    output_candidates_path: Path | None = None,
    output_pain_items_path: Path | None = None,
    report_path: Path | None = None,
    max_queries: int | None = None,
    max_results: int | None = None,
    use_cache: bool = True,
    skip_pilot: bool = False,
    llm_client=None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    cfg = load_yaml_section(config_path or DEFAULT_CONFIG_PATH, "query_calibration")
    out_cfg = cfg.get("output", {})
    pilot_cfg = cfg.get("pilot", {})
    q_path = Path(query_plan_path or out_cfg.get("calibrated_query_plan_path", "data/processed/mvp_d2/calibrated_query_plan_v2.jsonl"))
    if not q_path.exists():
        build_calibrated_query_plan(config_path=config_path, max_queries=max_queries)
    queries = read_jsonl(q_path)
    if max_queries is not None:
        queries = queries[:max_queries]

    cand_out = Path(output_candidates_path or out_cfg.get("calibrated_candidates_path", "data/processed/mvp_d2/calibrated_expansion_candidates.jsonl"))
    pain_out = Path(output_pain_items_path or out_cfg.get("calibrated_pain_items_path", "data/processed/mvp_d2/calibrated_expansion_pain_items.jsonl"))
    rel_out = Path(out_cfg.get("calibrated_domain_relevance_path", "data/processed/mvp_d2/calibrated_domain_relevance_scores.jsonl"))
    report = Path(report_path or out_cfg.get("calibrated_expansion_report_path", "outputs/mvp_d2/calibrated_expansion_report.md"))

    if skip_pilot or not bool(pilot_cfg.get("run_calibrated_pilot", True)):
        summary = _blocked_summary(
            queries=queries,
            blocked_reason="pilot_skipped",
            status="blocked",
        )
        write_jsonl(cand_out, [])
        write_jsonl(rel_out, [])
        write_jsonl(pain_out, [])
        _write_report(summary, report)
        return [], [], summary

    if candidates_path is None and not _search_provider_available():
        summary = _blocked_summary(
            queries=queries,
            blocked_reason="blocked_by_missing_search_provider",
            status="blocked",
        )
        write_jsonl(cand_out, [])
        write_jsonl(rel_out, [])
        write_jsonl(pain_out, [])
        _write_report(summary, report)
        return [], [], summary

    candidate_rows = read_jsonl(candidates_path) if candidates_path else []
    if max_results is not None:
        candidate_rows = candidate_rows[:max_results]
    max_total = int(max_results or pilot_cfg.get("max_total_new_signals", 80))
    candidate_rows = _dedupe_candidates(candidate_rows)[:max_total]
    _attach_query_metadata(candidate_rows, queries)
    write_jsonl(cand_out, candidate_rows)

    gate_allowed, gate_blocked = run_gate(candidate_rows)
    build_gate_report(gate_allowed, gate_blocked, Path("outputs/mvp_d2/calibrated_real_signal_gate_report.md"))

    if not candidate_rows:
        summary = _blocked_summary(
            queries=queries,
            blocked_reason="no_calibrated_candidates",
            status="no_candidates",
        )
        _write_report(summary, report)
        write_jsonl(rel_out, [])
        write_jsonl(pain_out, [])
        return [], [], summary

    _, pain_rows, extraction_summary = run_expansion_extraction(
        candidates_path=cand_out,
        relevance_output_path=rel_out,
        pain_output_path=pain_out,
        gate_report_path=Path("outputs/mvp_d2/calibrated_real_signal_gate_report.md"),
        report_path=Path("outputs/mvp_d2/calibrated_expansion_pain_extraction_report.md"),
        llm_pass_report_path=Path("outputs/mvp_d2/calibrated_llm_expansion_pass_report.md"),
        llm_client=llm_client,
        max_items=int(pilot_cfg.get("max_llm_candidates", 40)),
        use_cache=use_cache,
    )
    pain_rows = read_jsonl(pain_out)
    summary = {
        "generated_at": utc_now_iso(),
        "status": extraction_summary.get("status", "completed"),
        "blocked_reason": extraction_summary.get("blocked_reason"),
        "ran_pilot": True,
        "real_llm_run": bool(extraction_summary.get("real_llm_run", False)),
        "provider": extraction_summary.get("provider", "none"),
        "model": extraction_summary.get("model", "none"),
        "cache_enabled": use_cache,
        "total_queries": len(queries),
        "raw_new_signals": len(candidate_rows),
        "unique_new_signals": len(candidate_rows),
        "gate_allowed": int(extraction_summary.get("allowed_by_gate", len(gate_allowed))),
        "gate_blocked": int(extraction_summary.get("blocked_by_gate", len(gate_blocked))),
        "selected_for_llm": int(extraction_summary.get("selected_for_llm", 0)),
        "processed": int(extraction_summary.get("processed", len(pain_rows))),
        "should_extract_true": int(extraction_summary.get("should_extract_true", 0)),
        "strong": int(extraction_summary.get("strong", 0)),
        "medium": int(extraction_summary.get("medium", 0)),
        "weak": int(extraction_summary.get("weak", 0)),
        "reject": int(extraction_summary.get("rejected", 0)),
        "yield_rate": _yield_rate(int(extraction_summary.get("should_extract_true", 0)), int(extraction_summary.get("selected_for_llm", 0))),
        "by_query_type": dict(Counter((row.get("metadata") or {}).get("query_type", "unknown") for row in candidate_rows)),
        "by_source_category": dict(Counter((row.get("metadata") or {}).get("source_category", "unknown") for row in candidate_rows)),
        "by_seed": dict(Counter((row.get("metadata") or {}).get("seed_id", "unknown") for row in candidate_rows)),
    }
    _write_report(summary, report)
    return candidate_rows, pain_rows, summary


def _search_provider_available() -> bool:
    load_dotenv()
    keys = [
        "TAVILY_API_KEY",
        "SERPAPI_API_KEY",
        "SERP_API_KEY",
        "BING_SEARCH_API_KEY",
        "GOOGLE_SEARCH_API_KEY",
        "BRAVE_SEARCH_API_KEY",
        "DEMAND_RADAR_SEARCH_PROVIDER",
    ]
    return any(os.environ.get(key) for key in keys)


def _dedupe_candidates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for row in rows:
        key = (row.get("source_url") or row.get("candidate_id") or json.dumps(row, sort_keys=True)).strip().lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(row)
    return result


def _attach_query_metadata(rows: list[dict[str, Any]], queries: list[dict[str, Any]]) -> None:
    if not queries:
        return
    for index, row in enumerate(rows):
        query = queries[index % len(queries)]
        meta = dict(row.get("metadata") or {})
        meta.setdefault("seed_id", query.get("seed_id"))
        meta.setdefault("pain_item_id", query.get("pain_item_id"))
        meta.setdefault("seed_query_id", query.get("query_id"))
        meta.setdefault("query_type", query.get("query_type"))
        meta.setdefault("source_category", (query.get("metadata") or {}).get("source_category"))
        meta.setdefault("query_version", "v2")
        meta.setdefault("expansion_source", query.get("connector"))
        row["metadata"] = meta
        row.setdefault("collection_query", query.get("query"))


def _blocked_summary(queries: list[dict[str, Any]], blocked_reason: str, status: str) -> dict[str, Any]:
    return {
        "generated_at": utc_now_iso(),
        "status": status,
        "blocked_reason": blocked_reason,
        "ran_pilot": False,
        "real_llm_run": False,
        "provider": "none",
        "model": "none",
        "cache_enabled": True,
        "total_queries": len(queries),
        "raw_new_signals": 0,
        "unique_new_signals": 0,
        "gate_allowed": 0,
        "gate_blocked": 0,
        "selected_for_llm": 0,
        "processed": 0,
        "should_extract_true": 0,
        "strong": 0,
        "medium": 0,
        "weak": 0,
        "reject": 0,
        "yield_rate": 0.0,
        "by_query_type": dict(Counter(row.get("query_type", "unknown") for row in queries)),
        "by_source_category": dict(Counter((row.get("metadata") or {}).get("source_category", "unknown") for row in queries)),
        "by_seed": dict(Counter(row.get("seed_id", "unknown") for row in queries)),
    }


def _yield_rate(should_extract_true: int, selected_for_llm: int) -> float:
    return round(should_extract_true / selected_for_llm, 4) if selected_for_llm else 0.0


def _write_report(summary: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# MVP-D2 Calibrated Expansion Report",
        "",
        "## Summary",
        f"- status: {summary.get('status', 'completed')}",
        f"- blocked_reason: {summary.get('blocked_reason') or 'n/a'}",
        f"- ran_pilot: {str(summary.get('ran_pilot', False)).lower()}",
        f"- real_llm_run: {str(summary.get('real_llm_run', False)).lower()}",
        f"- provider: {summary.get('provider', 'none')}",
        f"- model: {summary.get('model', 'none')}",
        f"- cache_enabled: {str(summary.get('cache_enabled', True)).lower()}",
        f"- total_queries: {summary.get('total_queries', 0)}",
        f"- raw_new_signals: {summary.get('raw_new_signals', 0)}",
        f"- unique_new_signals: {summary.get('unique_new_signals', 0)}",
        f"- gate_allowed: {summary.get('gate_allowed', 0)}",
        f"- gate_blocked: {summary.get('gate_blocked', 0)}",
        f"- selected_for_llm: {summary.get('selected_for_llm', 0)}",
        f"- processed: {summary.get('processed', 0)}",
        f"- should_extract_true: {summary.get('should_extract_true', 0)}",
        f"- strong: {summary.get('strong', 0)}",
        f"- medium: {summary.get('medium', 0)}",
        f"- weak: {summary.get('weak', 0)}",
        f"- reject: {summary.get('reject', 0)}",
        f"- yield_rate: {summary.get('yield_rate', 0.0)}",
        f"- by_query_type: {json.dumps(summary.get('by_query_type', {}), ensure_ascii=False)}",
        f"- by_source_category: {json.dumps(summary.get('by_source_category', {}), ensure_ascii=False)}",
        f"- by_seed: {json.dumps(summary.get('by_seed', {}), ensure_ascii=False)}",
    ]
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
