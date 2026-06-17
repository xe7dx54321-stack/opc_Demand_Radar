"""Read-only UI service for MVP-D2 diagnostics and query calibration."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            rows.append(item)
    return rows


def _load_report_kv(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        return {}
    data: dict[str, Any] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        text = line.strip()
        if not text.startswith("- ") or ":" not in text:
            continue
        key, value = text[2:].split(":", 1)
        value = value.strip()
        if value.lower() in {"true", "false"}:
            data[key.strip()] = value.lower() == "true"
            continue
        try:
            data[key.strip()] = int(value)
            continue
        except ValueError:
            pass
        try:
            data[key.strip()] = float(value)
            continue
        except ValueError:
            pass
        try:
            data[key.strip()] = json.loads(value)
        except Exception:
            data[key.strip()] = None if value == "n/a" else value
    return data


def get_mvp_d2_overview() -> dict[str, Any]:
    diagnostics = get_reject_diagnostics()
    source_scores = get_source_quality_scores()
    queries = get_calibrated_query_plan()
    pilot = _load_report_kv("outputs/mvp_d2/calibrated_expansion_report.md")
    comparison = _load_report_kv("outputs/mvp_d2/d2_comparison_report.md")
    summary = _load_report_kv("outputs/mvp_d2/mvp_d2_summary_report.md")
    return {
        "total_rejected": len(diagnostics),
        "source_rows": len(source_scores),
        "v2_queries": len(queries),
        "ran_pilot": pilot.get("ran_pilot", False),
        "blocked_reason": pilot.get("blocked_reason"),
        "should_extract_true": pilot.get("should_extract_true", 0),
        "yield_rate": pilot.get("yield_rate", 0.0),
        "comparison_result": comparison.get("result", summary.get("comparison_result")),
        "engineering_acceptance": summary.get("engineering_acceptance"),
        "product_acceptance": summary.get("product_acceptance"),
        "reason": summary.get("reason"),
    }


def get_reject_diagnostics() -> list[dict[str, Any]]:
    return _load_jsonl("data/processed/mvp_d2/reject_diagnostics.jsonl")


def get_source_quality_scores() -> list[dict[str, Any]]:
    return _load_jsonl("data/processed/mvp_d2/source_quality_scores.jsonl")


def get_calibrated_query_plan() -> list[dict[str, Any]]:
    return _load_jsonl("data/processed/mvp_d2/calibrated_query_plan_v2.jsonl")


def get_calibrated_pain_items() -> list[dict[str, Any]]:
    return _load_jsonl("data/processed/mvp_d2/calibrated_expansion_pain_items.jsonl")
