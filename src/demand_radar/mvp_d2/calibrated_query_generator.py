"""Generate MVP-D2 calibrated query plan v2."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from demand_radar.mvp_d.seed_schema import SeededQuery
from demand_radar.mvp_d2.query_pattern_library import (
    DOMAIN_RECOMMENDED_QUERIES,
    NEGATIVE_TERMS,
    QUERY_PATTERNS,
    competitor_terms,
    connector_for_query_type,
    persona_terms,
    source_category_for_query_type,
    workflow_terms,
)
from demand_radar.mvp_d2.utils import load_yaml_section, read_jsonl, write_jsonl
from demand_radar.state.raw_store import next_ids, utc_now_iso

DEFAULT_CONFIG_PATH = Path("configs/query_calibration_config.yaml")


def build_calibrated_query_plan(
    config_path: Path | None = None,
    seed_profiles_path: Path | None = None,
    output_path: Path | None = None,
    report_path: Path | None = None,
    max_queries: int | None = None,
) -> list[SeededQuery]:
    cfg = load_yaml_section(config_path or DEFAULT_CONFIG_PATH, "query_calibration")
    q_cfg = cfg.get("query_generation", {})
    out_cfg = cfg.get("output", {})
    seed_path = seed_profiles_path or Path(
        (cfg.get("input") or {}).get("seed_profiles_path", "data/processed/mvp_d/seed_profiles.jsonl")
    )
    seeds = read_jsonl(seed_path)
    max_per_seed = int(q_cfg.get("max_queries_per_seed", 12))
    min_per_seed = int(q_cfg.get("min_queries_per_seed", 6))
    max_total = int(max_queries or q_cfg.get("max_total_queries", 48))
    negative_terms = list(cfg.get("negative_terms") or NEGATIVE_TERMS)

    queries: list[SeededQuery] = []
    now = utc_now_iso()

    for seed in seeds:
        seed_queries = _queries_for_seed(seed, max_per_seed=max_per_seed, min_per_seed=min_per_seed)
        query_ids = next_ids(f"d2_query_{seed.get('seed_id', 'seed')}_", [], len(seed_queries))
        for query_id, item in zip(query_ids, seed_queries, strict=True):
            query_type = item["query_type"]
            queries.append(
                SeededQuery(
                    query_id=query_id,
                    seed_id=str(seed.get("seed_id") or ""),
                    pain_item_id=str(seed.get("pain_item_id") or ""),
                    connector=item.get("connector") or connector_for_query_type(query_type),
                    query=item["query"],
                    query_type=query_type,
                    expected_signal_type=item.get("expected_signal_type") or "pain",
                    priority=item.get("priority") or seed.get("expansion_priority") or "medium",
                    negative_terms=negative_terms,
                    created_at=now,
                    metadata={
                        "source_category": item.get("source_category") or source_category_for_query_type(query_type),
                        "query_version": "v2",
                        "calibration_goal": "pain_evidence_discovery",
                    },
                )
            )
    queries = _dedupe_queries(queries)[:max_total]
    out_path = Path(output_path or out_cfg.get("calibrated_query_plan_path", "data/processed/mvp_d2/calibrated_query_plan_v2.jsonl"))
    write_jsonl(out_path, queries)
    build_calibrated_query_plan_report(
        queries,
        Path(report_path or out_cfg.get("query_calibration_report_path", "outputs/mvp_d2/calibrated_query_plan_report.md")),
    )
    return queries


def _queries_for_seed(seed: dict[str, Any], max_per_seed: int, min_per_seed: int) -> list[dict[str, str]]:
    workflows = workflow_terms(seed)
    personas = persona_terms(seed)
    competitors = competitor_terms(seed)
    rows: list[dict[str, str]] = []

    for query_type, query in DOMAIN_RECOMMENDED_QUERIES:
        if _seed_relevant(query, workflows, personas):
            rows.append(_query_row(query_type, query))

    for pattern in QUERY_PATTERNS:
        for workflow in workflows[:2]:
            persona = personas[0]
            competitor = competitors[0]
            query = pattern.template.format(
                workflow=workflow,
                persona=persona,
                competitor_or_tool=competitor,
            )
            rows.append(
                {
                    "query_type": pattern.query_type,
                    "query": query,
                    "expected_signal_type": pattern.expected_signal_type,
                    "priority": pattern.priority,
                    "source_category": pattern.source_category,
                    "connector": pattern.connector,
                }
            )
            if len(rows) >= max_per_seed:
                break
        if len(rows) >= max_per_seed:
            break

    if len(rows) < min_per_seed:
        for query_type, query in DOMAIN_RECOMMENDED_QUERIES:
            rows.append(_query_row(query_type, query))
            if len(rows) >= min_per_seed:
                break
    return _dedupe_query_rows(rows)[:max_per_seed]


def _query_row(query_type: str, query: str) -> dict[str, str]:
    return {
        "query_type": query_type,
        "query": query,
        "expected_signal_type": {
            "pain_phrase": "pain",
            "complaint_phrase": "complaint",
            "workaround_phrase": "workaround",
            "manual_workflow": "workflow",
            "spreadsheet_workaround": "workaround",
            "buying_intent": "paid_signal",
            "alternative_tool": "comparison",
            "competitor_review": "comparison",
            "community_question": "workflow",
        }.get(query_type, "pain"),
        "priority": "high" if query_type in {"pain_phrase", "complaint_phrase", "manual_workflow", "spreadsheet_workaround"} else "medium",
        "source_category": source_category_for_query_type(query_type),
        "connector": connector_for_query_type(query_type),
    }


def _seed_relevant(query: str, workflows: list[str], personas: list[str]) -> bool:
    lowered = query.lower()
    if any(token.lower() in lowered for wf in workflows for token in wf.split()):
        return True
    return any(persona.lower() in lowered for persona in personas)


def _dedupe_query_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    deduped: list[dict[str, str]] = []
    for row in rows:
        key = row["query"].lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def _dedupe_queries(queries: list[SeededQuery]) -> list[SeededQuery]:
    seen: set[tuple[str, str]] = set()
    result: list[SeededQuery] = []
    for query in queries:
        key = (query.seed_id, query.query.lower())
        if key in seen:
            continue
        seen.add(key)
        result.append(query)
    return result


def build_calibrated_query_plan_report(
    queries: list[SeededQuery],
    report_path: Path = Path("outputs/mvp_d2/calibrated_query_plan_report.md"),
) -> Path:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    by_seed = Counter(query.seed_id for query in queries)
    by_connector = Counter(query.connector for query in queries)
    by_type = Counter(query.query_type for query in queries)
    lines = [
        "# MVP-D2 Calibrated Query Plan Report",
        "",
        "## Summary",
        f"- total_queries: {len(queries)}",
        f"- queries_by_seed: {json.dumps(dict(by_seed), ensure_ascii=False)}",
        f"- queries_by_connector: {json.dumps(dict(by_connector), ensure_ascii=False)}",
        f"- query_types: {json.dumps(dict(by_type), ensure_ascii=False)}",
        "",
        "## How V2 Differs From V1",
        "- V2 优先搜索 pain / complaint / workaround / manual workflow，而不是泛泛搜索产品或项目。",
        "- V2 强制保留 seed_id、pain_item_id、query_type 和 source_category，便于后续归因。",
        "- V2 带负向词，减少 recipe、fitness、game、generic chatbot 等域外命中。",
        "",
        "## Query Examples",
    ]
    for query in queries[:40]:
        source_category = (query.metadata or {}).get("source_category", "unknown")
        lines.append(
            "- "
            f"{query.query_id} | seed={query.seed_id} | {query.connector} | "
            f"{query.query_type} | {source_category} | {query.query}"
        )
    if not queries:
        lines.append("No calibrated queries generated.")
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return report_path
