"""MVP-D seeded acquisition using existing opc-foundation connectors."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import yaml
from opc_foundation.run.run_context import RunContext
from opc_foundation.run.time_utils import utcnow_iso
from opc_foundation.sources.connectors import GitHubIssuesConnector, HackerNewsConnector, RssConnector
from opc_foundation.sources.source_schema import SourceDefinition, SourceQuery
from opc_foundation.signals import dedupe_raw_signals

from demand_radar.acquisition.domain_source_config import get_source_registry_path
from demand_radar.acquisition.evidence_candidate_builder import build_evidence_candidates
from demand_radar.mvp_d.real_signal_gate import is_real_signal
from demand_radar.mvp_d.seed_schema import SeededQuery
from demand_radar.state.raw_store import next_ids


_CONFIG_PATH = Path("configs/seeded_expansion_config.yaml")
_CONNECTORS = {
    "hacker_news": HackerNewsConnector,
    "github_issues": GitHubIssuesConnector,
    "rss": RssConnector,
}


def _load_cfg(path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or _CONFIG_PATH
    with cfg_path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle).get("seeded_expansion", {})


def _read_queries(path: Path) -> list[SeededQuery]:
    if not path.exists():
        return []
    return [
        SeededQuery.model_validate(json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _read_existing_urls(path: Path) -> set[str]:
    if not path.exists():
        return set()
    urls: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        url = (row.get("source_url") or "").strip().lower()
        if url:
            urls.add(url)
    return urls


def _source_definition_for_query(
    query: SeededQuery,
    domain_id: str,
    feed_url: str | None = None,
) -> SourceDefinition:
    source_type = {
        "hacker_news": "community_discussion",
        "github_issues": "github_issue",
        "rss": "rss",
    }.get(query.connector, query.connector)
    return SourceDefinition(
        source_id=f"mvp_d_{query.connector}",
        source_name=f"MVP-D {query.connector}",
        source_type=source_type,
        connector=query.connector,
        enabled=True,
        base_url=feed_url,
        default_queries=[query.query] if query.connector != "rss" else [],
        tags=[domain_id, "mvp_d"],
        trust_weight=0.60 if query.connector == "rss" else 0.85,
        metadata={"feed_url": feed_url} if feed_url else {},
    )


def _load_rss_feed_urls(domain_id: str) -> list[str]:
    registry_path = get_source_registry_path(domain_id)
    if not registry_path.exists():
        return []
    data = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    urls: list[str] = []
    for source in data.get("sources", []):
        if source.get("connector") != "rss" or not source.get("enabled", True):
            continue
        for url in (source.get("metadata") or {}).get("feed_urls", []):
            if url and url not in urls:
                urls.append(url)
    return urls


def run_seeded_acquisition(
    config_path: Path | None = None,
    query_plan_path: Path | None = None,
    existing_candidates_path: Path | None = None,
    output_path: Path | None = None,
    report_path: Path = Path("outputs/mvp_d/seeded_acquisition_report.md"),
    max_queries: int | None = None,
    max_results: int | None = None,
) -> tuple[list[dict], dict[str, Any]]:
    cfg = _load_cfg(config_path)
    acquisition_cfg = cfg.get("acquisition", {})
    output_cfg = cfg.get("output", {})
    input_cfg = cfg.get("input", {})
    domain_id = cfg.get("domain_id", "ai_investment_tracking")
    domain_title = cfg.get("domain_title_zh", "投资人 / 研究员 AI 产业跟踪与项目初筛")
    q_path = query_plan_path or Path(
        output_cfg.get("query_plan_path", "data/processed/mvp_d/seeded_query_plan.jsonl")
    )
    out_path = output_path or Path(
        output_cfg.get(
            "expansion_evidence_candidates_path",
            "data/processed/mvp_d/expansion_evidence_candidates.jsonl",
        )
    )
    existing_path = existing_candidates_path or Path(
        input_cfg.get("existing_candidates_path", "data/processed/acquisition/evidence_candidates.jsonl")
    )
    max_items_per_query = int(max_results or acquisition_cfg.get("max_results_per_query", 20))
    max_total = int(acquisition_cfg.get("max_total_new_signals", 120))
    queries = _read_queries(q_path)
    if max_queries is not None:
        queries = queries[:max_queries]

    context = RunContext(pipeline_name=f"demand_radar_mvp_d_{domain_id}")
    raw_signals = []
    errors: list[str] = []
    warnings: list[str] = []
    rss_urls = _load_rss_feed_urls(domain_id)

    for query in queries:
        connector_cls = _CONNECTORS.get(query.connector)
        if connector_cls is None:
            warnings.append(f"unsupported connector: {query.connector}")
            continue

        query_items: list[tuple[SourceDefinition, SourceQuery]] = []
        if query.connector == "rss":
            if not rss_urls:
                warnings.append("rss query skipped: no feed_urls configured")
                continue
            for feed_url in rss_urls:
                source = _source_definition_for_query(query, domain_id, feed_url=feed_url)
                source_query = SourceQuery(
                    query_id=query.query_id,
                    source_id=source.source_id,
                    url=feed_url,
                    max_items=max_items_per_query,
                    metadata={
                        "feed_url": feed_url,
                        "seed_id": query.seed_id,
                        "pain_item_id": query.pain_item_id,
                        "seed_query_id": query.query_id,
                        "seed_query": query.query,
                    },
                )
                query_items.append((source, source_query))
        else:
            source = _source_definition_for_query(query, domain_id)
            source_query = SourceQuery(
                query_id=query.query_id,
                source_id=source.source_id,
                query=query.query,
                max_items=max_items_per_query,
                metadata={
                    "seed_id": query.seed_id,
                    "pain_item_id": query.pain_item_id,
                    "seed_query_id": query.query_id,
                    "seed_query": query.query,
                },
            )
            query_items.append((source, source_query))

        for source, source_query in query_items:
            try:
                result = connector_cls().fetch(source_query, source, context)
                for signal in result.raw_signals:
                    signal.metadata.update(source_query.metadata)
                    signal.metadata["expansion_run_id"] = context.run_id
                    signal.metadata["expansion_source"] = query.connector
                raw_signals.extend(result.raw_signals)
                errors.extend(result.errors)
                warnings.extend(result.warnings)
            except Exception as exc:
                errors.append(f"{query.connector}:{query.query_id}:{exc}")

    dedupe_result = dedupe_raw_signals(raw_signals, by="both") if raw_signals else None
    unique_signals = dedupe_result.unique_signals if dedupe_result else []
    duplicate_count = dedupe_result.duplicate_count if dedupe_result else 0
    existing_urls = _read_existing_urls(existing_path)
    filtered_signals = []
    deduped_against_existing = 0
    for signal in unique_signals:
        url = (signal.source_url or "").strip().lower()
        if url and url in existing_urls:
            deduped_against_existing += 1
            continue
        filtered_signals.append(signal)
        if len(filtered_signals) >= max_total:
            break

    candidates = build_evidence_candidates(filtered_signals, domain_id, domain_title)
    candidate_ids = next_ids("mvp_d_cand_", [], len(candidates))
    candidate_rows: list[dict] = []
    gate_allowed = 0
    gate_blocked = 0
    for index, candidate in enumerate(candidates):
        row = candidate.model_dump()
        row["candidate_id"] = candidate_ids[index]
        row["metadata"] = dict(row.get("metadata") or {})
        gate_result = is_real_signal(row)
        if gate_result.allow:
            gate_allowed += 1
        else:
            gate_blocked += 1
        candidate_rows.append(row)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in candidate_rows)
        + ("\n" if candidate_rows else ""),
        encoding="utf-8",
    )
    summary = {
        "run_id": context.run_id,
        "started_at": context.started_at,
        "ended_at": utcnow_iso(),
        "raw_new_signals": len(raw_signals),
        "unique_new_signals": len(unique_signals),
        "duplicates": duplicate_count,
        "deduped_against_existing": deduped_against_existing,
        "written_candidates": len(candidate_rows),
        "allowed_by_gate": gate_allowed,
        "blocked_by_gate": gate_blocked,
        "by_source": dict(Counter(row.get("source_type") for row in candidate_rows)),
        "source_url_present": sum(1 for row in candidate_rows if row.get("source_url")),
        "errors": errors,
        "warnings": warnings,
    }
    _write_report(summary, report_path)
    return candidate_rows, summary


def _write_report(summary: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# MVP-D Seeded Acquisition Report",
        "",
        f"- raw_new_signals: {summary['raw_new_signals']}",
        f"- unique_new_signals: {summary['unique_new_signals']}",
        f"- duplicates: {summary['duplicates']}",
        f"- deduped_against_existing: {summary['deduped_against_existing']}",
        f"- written_candidates: {summary['written_candidates']}",
        f"- allowed_by_gate: {summary['allowed_by_gate']}",
        f"- blocked_by_gate: {summary['blocked_by_gate']}",
        f"- source_url_present: {summary['source_url_present']}",
        "",
        "## By Source",
    ]
    for source, count in sorted(summary["by_source"].items()):
        lines.append(f"- {source}: {count}")
    lines.extend(["", "## Errors / Warnings"])
    if not summary["errors"] and not summary["warnings"]:
        lines.append("- none")
    for item in summary["errors"][:20]:
        lines.append(f"- error: {item}")
    for item in summary["warnings"][:20]:
        lines.append(f"- warning: {item}")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
