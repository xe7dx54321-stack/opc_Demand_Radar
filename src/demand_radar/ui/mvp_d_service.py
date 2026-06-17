"""Read-only UI service for MVP-D seeded evidence expansion."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            rows.append(item)
    return rows


def _load_json(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def get_mvp_d_overview() -> dict[str, Any]:
    seeds = get_seed_profiles()
    queries = get_seeded_query_plan()
    candidates = get_expansion_candidates()
    pains = get_expansion_pain_items()
    consolidations = get_seed_consolidations()
    themes = get_demand_themes()
    run_summary = _load_json("outputs/run_summary.json")
    return {
        "eligible_seeds": len(seeds),
        "total_queries": len(queries),
        "expansion_candidates": len(candidates),
        "new_extracted_pain": sum(1 for item in pains if item.get("should_extract")),
        "consolidations": len(consolidations),
        "themes": len(themes),
        "engineering_acceptance": run_summary.get("engineering_acceptance"),
        "product_acceptance": run_summary.get("product_acceptance"),
        "can_enter_second_review": run_summary.get("can_enter_second_review"),
        "can_enter_product_discovery": run_summary.get("can_enter_product_discovery"),
        "reason": run_summary.get("reason"),
    }


def get_seed_profiles() -> list[dict[str, Any]]:
    return _load_jsonl("data/processed/mvp_d/seed_profiles.jsonl")


def get_seeded_query_plan() -> list[dict[str, Any]]:
    return _load_jsonl("data/processed/mvp_d/seeded_query_plan.jsonl")


def get_expansion_candidates() -> list[dict[str, Any]]:
    return _load_jsonl("data/processed/mvp_d/expansion_evidence_candidates.jsonl")


def get_expansion_pain_items() -> list[dict[str, Any]]:
    return _load_jsonl("data/processed/mvp_d/expansion_pain_items.jsonl")


def get_seed_consolidations() -> list[dict[str, Any]]:
    return _load_jsonl("data/processed/mvp_d/seed_evidence_consolidation.jsonl")


def get_demand_themes() -> list[dict[str, Any]]:
    return _load_jsonl("data/processed/mvp_d/consolidated_evidence_themes.jsonl")


def get_d5_overview() -> dict[str, Any]:
    themes = get_d5_demand_themes()
    queue = get_d5_theme_review_queue()
    deduped = _load_jsonl("data/processed/d5/deduped_pain_items.jsonl")
    source_groups = _load_jsonl("data/processed/d5/source_groups.jsonl")
    run_summary = _load_json("outputs/run_summary.json")
    return {
        "themes": len(themes),
        "queue_count": len(queue),
        "deduped_representatives": sum(1 for item in deduped if item.get("is_representative")),
        "source_groups": len(source_groups),
        "pursue_candidate": sum(1 for theme in themes if theme.get("action_recommendation") == "pursue_candidate"),
        "watch": sum(1 for theme in themes if theme.get("action_recommendation") == "watch"),
        "needs_more_evidence": sum(1 for theme in themes if theme.get("action_recommendation") == "needs_more_evidence"),
        "reject": sum(1 for theme in themes if theme.get("action_recommendation") == "reject"),
        "engineering_acceptance": run_summary.get("d5_engineering_acceptance"),
        "product_acceptance": run_summary.get("d5_product_acceptance"),
        "can_enter_theme_review": run_summary.get("d5_can_enter_theme_review"),
        "can_enter_product_discovery": run_summary.get("d5_can_enter_product_discovery"),
        "reason": run_summary.get("d5_reason"),
    }


def get_d5_demand_themes() -> list[dict[str, Any]]:
    return _load_jsonl("data/processed/d5/demand_themes.jsonl")


def get_d5_theme_review_queue() -> list[dict[str, Any]]:
    return _load_jsonl("data/processed/d5/theme_review_queue.jsonl")


def get_d5_source_groups() -> list[dict[str, Any]]:
    return _load_jsonl("data/processed/d5/source_groups.jsonl")
