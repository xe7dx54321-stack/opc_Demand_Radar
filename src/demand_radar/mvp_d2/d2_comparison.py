"""Compare MVP-D v1 expansion yield with MVP-D2 calibrated pilot."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from demand_radar.mvp_d2.utils import load_yaml_section, read_jsonl, read_markdown_kv

DEFAULT_QUERY_CONFIG_PATH = Path("configs/query_calibration_config.yaml")


def compare_expansion_v1_v2(
    query_config_path: Path | None = None,
    v1_report_path: Path = Path("outputs/mvp_d/expansion_pain_extraction_report.md"),
    v1_query_plan_path: Path = Path("data/processed/mvp_d/seeded_query_plan.jsonl"),
    v1_candidates_path: Path = Path("data/processed/mvp_d/expansion_evidence_candidates.jsonl"),
    v2_report_path: Path | None = None,
    v2_query_plan_path: Path | None = None,
    report_path: Path | None = None,
) -> dict[str, Any]:
    cfg = load_yaml_section(query_config_path or DEFAULT_QUERY_CONFIG_PATH, "query_calibration")
    out_cfg = cfg.get("output", {})
    v2_report = Path(v2_report_path or out_cfg.get("calibrated_expansion_report_path", "outputs/mvp_d2/calibrated_expansion_report.md"))
    v2_query_plan = Path(v2_query_plan_path or out_cfg.get("calibrated_query_plan_path", "data/processed/mvp_d2/calibrated_query_plan_v2.jsonl"))
    report = Path(report_path or out_cfg.get("d2_comparison_report_path", "outputs/mvp_d2/d2_comparison_report.md"))

    v1_metrics = _v1_metrics(v1_report_path, v1_query_plan_path, v1_candidates_path)
    v2_metrics = _v2_metrics(v2_report, v2_query_plan)
    result = compare_yield(v1_metrics, v2_metrics)
    payload = {
        "v1": v1_metrics,
        "v2": v2_metrics,
        "result": result,
        "explanation": _explanation(v1_metrics, v2_metrics, result),
    }
    build_d2_comparison_report(payload, report)
    return payload


def compare_yield(v1: dict[str, Any], v2: dict[str, Any]) -> str:
    if v2.get("status") == "blocked" or v2.get("blocked_reason"):
        return "blocked"
    if int(v2.get("selected_for_llm", 0)) == 0:
        return "blocked"
    v1_yield = float(v1.get("yield_rate", 0.0))
    v2_yield = float(v2.get("yield_rate", 0.0))
    if v2_yield > v1_yield:
        return "improved"
    if v2_yield < v1_yield:
        return "worse"
    return "no_change"


def build_d2_comparison_report(payload: dict[str, Any], report_path: Path) -> Path:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    v1 = payload["v1"]
    v2 = payload["v2"]
    lines = [
        "# MVP-D2 V1 vs V2 Expansion Comparison",
        "",
        "## V1",
        f"- total_queries: {v1.get('total_queries', 0)}",
        f"- raw_new_signals: {v1.get('raw_new_signals', 0)}",
        f"- unique_new_signals: {v1.get('unique_new_signals', 0)}",
        f"- gate_allowed: {v1.get('gate_allowed', 0)}",
        f"- selected_for_llm: {v1.get('selected_for_llm', 0)}",
        f"- should_extract_true: {v1.get('should_extract_true', 0)}",
        f"- yield_rate: {v1.get('yield_rate', 0.0)}",
        "",
        "## V2",
        f"- total_queries: {v2.get('total_queries', 0)}",
        f"- raw_new_signals: {v2.get('raw_new_signals', 0)}",
        f"- unique_new_signals: {v2.get('unique_new_signals', 0)}",
        f"- gate_allowed: {v2.get('gate_allowed', 0)}",
        f"- selected_for_llm: {v2.get('selected_for_llm', 0)}",
        f"- should_extract_true: {v2.get('should_extract_true', 0)}",
        f"- yield_rate: {v2.get('yield_rate', 0.0)}",
        f"- status: {v2.get('status', 'unknown')}",
        f"- blocked_reason: {v2.get('blocked_reason') or 'n/a'}",
        "",
        "## Result",
        f"- result: {payload['result']}",
        f"- explanation: {payload['explanation']}",
        "",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def _v1_metrics(report_path: Path, query_plan_path: Path, candidates_path: Path) -> dict[str, Any]:
    report = read_markdown_kv(report_path)
    candidate_rows = read_jsonl(candidates_path)
    query_rows = read_jsonl(query_plan_path)
    selected = int(report.get("selected_for_llm", 0))
    extracted = int(report.get("should_extract_true", 0))
    return {
        "total_queries": len(query_rows),
        "raw_new_signals": int(report.get("total_candidates", len(candidate_rows))),
        "unique_new_signals": len(candidate_rows),
        "gate_allowed": int(report.get("allowed_by_gate", report.get("selected_for_llm", 0))),
        "selected_for_llm": selected,
        "should_extract_true": extracted,
        "yield_rate": round(extracted / selected, 4) if selected else 0.0,
        "status": report.get("status", "completed"),
        "blocked_reason": report.get("blocked_reason"),
    }


def _v2_metrics(report_path: Path, query_plan_path: Path) -> dict[str, Any]:
    report = read_markdown_kv(report_path)
    query_rows = read_jsonl(query_plan_path)
    selected = int(report.get("selected_for_llm", 0))
    extracted = int(report.get("should_extract_true", 0))
    return {
        "total_queries": len(query_rows),
        "raw_new_signals": int(report.get("raw_new_signals", 0)),
        "unique_new_signals": int(report.get("unique_new_signals", 0)),
        "gate_allowed": int(report.get("gate_allowed", 0)),
        "selected_for_llm": selected,
        "should_extract_true": extracted,
        "yield_rate": float(report.get("yield_rate", round(extracted / selected, 4) if selected else 0.0)),
        "status": report.get("status", "unknown"),
        "blocked_reason": report.get("blocked_reason") if report.get("blocked_reason") != "n/a" else None,
    }


def _explanation(v1: dict[str, Any], v2: dict[str, Any], result: str) -> str:
    if result == "blocked":
        return f"V2 pilot 未完成真实验证：{v2.get('blocked_reason') or v2.get('status') or 'unknown'}。"
    if result == "improved":
        return f"V2 yield {v2.get('yield_rate')} 高于 V1 yield {v1.get('yield_rate')}。"
    if result == "worse":
        return f"V2 yield {v2.get('yield_rate')} 低于 V1 yield {v1.get('yield_rate')}。"
    return f"V2 yield 与 V1 相同，均为 {v2.get('yield_rate')}。"
