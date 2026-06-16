"""Acquisition pipeline: orchestrates source fetching -> EvidenceCandidate."""
from __future__ import annotations
from collections import Counter
from pathlib import Path

from opc_foundation.sources import SourceRegistry
from opc_foundation.sources.connectors import (
    HackerNewsConnector,
    GitHubIssuesConnector,
    RssConnector,
    ManualUrlConnector,
)
from opc_foundation.sources.source_schema import SourceQuery
from opc_foundation.signals import dedupe_raw_signals
from opc_foundation.run.run_context import RunContext
from opc_foundation.run.id_generator import new_id
from opc_foundation.run.time_utils import utcnow_iso

from .acquisition_schema import AcquisitionRunSummary, EvidenceCandidate
from .domain_source_config import load_domain_config, get_domain_title_zh, get_source_registry_path
from .evidence_candidate_builder import build_evidence_candidates
from .acquisition_store import write_raw_signals, write_evidence_candidates, append_run_log


_CONNECTOR_MAP = {
    "hacker_news": HackerNewsConnector,
    "github_issues": GitHubIssuesConnector,
    "rss": RssConnector,
    "manual_url": ManualUrlConnector,
}

_MAX_ITEMS_PER_QUERY = 20


def _make_connector(connector_id: str, source_meta: dict):
    cls = _CONNECTOR_MAP.get(connector_id)
    if cls is None:
        return None
    return cls()


def run_acquisition(
    domain_id: str,
    domain_config_dir: Path | None = None,
    source_registry_path: Path | None = None,
    raw_output_path: Path | None = None,
    candidates_output_path: Path | None = None,
    run_log_path: Path | None = None,
    max_items_per_query: int = _MAX_ITEMS_PER_QUERY,
) -> tuple[AcquisitionRunSummary, list[EvidenceCandidate]]:
    """Run the full acquisition pipeline for a domain."""
    domain_cfg = load_domain_config(domain_id, config_dir=domain_config_dir)
    domain_title_zh = get_domain_title_zh(domain_cfg)

    reg_path = source_registry_path or get_source_registry_path(domain_id)
    if not reg_path.exists():
        raise FileNotFoundError(f"Source registry not found: {reg_path}")

    registry = SourceRegistry.from_yaml(reg_path)
    sources = registry.get_enabled_sources()

    context = RunContext(pipeline_name=f"demand_radar_{domain_id}")
    run_id = context.run_id
    started_at = context.started_at

    all_raw_signals = []
    all_errors: list[str] = []
    all_warnings: list[str] = []
    source_counts: dict[str, int] = {}

    for source in sources:
        connector_id = source.connector
        connector = _make_connector(connector_id, source.metadata)
        if connector is None:
            all_warnings.append(f"Unknown connector: {connector_id} for source {source.source_id}")
            continue

        queries = source.default_queries or []
        feed_urls = source.metadata.get("feed_urls", [])
        input_csv = source.metadata.get("input_csv")
        source_signals = 0

        # Build query list
        query_items = []
        if queries:
            for q in queries:
                query_items.append({"query": q, "url": None, "metadata": {}})
        elif feed_urls:
            for feed_url in feed_urls:
                query_items.append({"query": None, "url": feed_url, "metadata": {"feed_url": feed_url}})
        elif input_csv:
            csv_path = Path(input_csv)
            if not csv_path.exists():
                all_warnings.append(f"Manual URL CSV not found: {input_csv} (skipping {source.source_id})")
                continue
            query_items.append({"query": None, "url": str(csv_path), "metadata": {"csv_path": str(csv_path)}})
        else:
            all_warnings.append(f"No queries or feed_urls for source {source.source_id}")
            continue

        for qi in query_items:
            sq = SourceQuery(
                query_id=new_id("q_"),
                source_id=source.source_id,
                query=qi.get("query"),
                url=qi.get("url"),
                max_items=max_items_per_query,
                metadata=qi.get("metadata", {}),
            )
            try:
                result = connector.fetch(sq, source, context)
                all_raw_signals.extend(result.raw_signals)
                source_signals += len(result.raw_signals)
                all_errors.extend(result.errors)
                all_warnings.extend(result.warnings)
            except Exception as exc:
                all_errors.append(f"Connector {connector_id} fetch error: {exc}")

        source_counts[source.source_id] = source_signals

    # Deduplicate
    if all_raw_signals:
        dedupe_result = dedupe_raw_signals(all_raw_signals, by="both")
        unique_signals = dedupe_result.unique_signals
        dup_count = dedupe_result.duplicate_count
    else:
        unique_signals = []
        dup_count = 0

    # Build candidates
    candidates = build_evidence_candidates(unique_signals, domain_id, domain_title_zh)

    # Counts
    by_source_type = dict(Counter(c.source_type for c in candidates))
    valid_n = sum(1 for c in candidates if c.validation_status == "valid")
    warn_n = sum(1 for c in candidates if c.validation_status == "warning")
    inv_n = sum(1 for c in candidates if c.validation_status == "invalid")

    summary = AcquisitionRunSummary(
        run_id=run_id,
        domain_id=domain_id,
        started_at=started_at,
        ended_at=utcnow_iso(),
        raw_signal_count=len(all_raw_signals),
        unique_signal_count=len(unique_signals),
        duplicate_count=dup_count,
        evidence_candidate_count=len(candidates),
        valid_candidate_count=valid_n,
        warning_candidate_count=warn_n,
        invalid_candidate_count=inv_n,
        by_source=source_counts,
        by_source_type=by_source_type,
        errors=all_errors,
        warnings=all_warnings,
    )

    # Persist
    write_raw_signals([s.model_dump() for s in unique_signals], raw_output_path)
    write_evidence_candidates(candidates, candidates_output_path)
    append_run_log(summary, run_log_path)

    return summary, candidates
