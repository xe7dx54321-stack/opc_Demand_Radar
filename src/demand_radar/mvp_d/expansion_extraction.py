"""MVP-D expansion domain relevance and pain extraction."""
from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from demand_radar.mvp_b.domain_relevance_filter import run_domain_relevance_filter
from demand_radar.mvp_b.pain_extraction_runner import run_pain_extraction
from demand_radar.mvp_d.real_signal_gate import build_gate_report, run_gate

_CONFIG_PATH = Path("configs/seeded_expansion_config.yaml")


def _load_cfg(path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or _CONFIG_PATH
    with cfg_path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle).get("seeded_expansion", {})


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_jsonl(path: Path, rows: list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(row.model_dump_json() if hasattr(row, "model_dump_json") else json.dumps(row, ensure_ascii=False) for row in rows)
        + ("\n" if rows else ""),
        encoding="utf-8",
    )


class _EnvLLMClient:
    def __init__(self) -> None:
        self.provider = os.getenv("LLM_PROVIDER", "none")
        self.model = os.getenv("LLM_MODEL", "none")

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        raise RuntimeError("No real LLM client configured for MVP-D in this environment")


def run_expansion_extraction(
    config_path: Path | None = None,
    candidates_path: Path | None = None,
    relevance_output_path: Path | None = None,
    pain_output_path: Path | None = None,
    gate_report_path: Path = Path("outputs/mvp_d/real_signal_gate_report.md"),
    report_path: Path = Path("outputs/mvp_d/expansion_pain_extraction_report.md"),
    llm_client=None,
    max_items: int | None = None,
    use_cache: bool = True,
) -> tuple[list[dict], list[dict], dict[str, Any]]:
    cfg = _load_cfg(config_path)
    output_cfg = cfg.get("output", {})
    cand_path = candidates_path or Path(output_cfg.get("expansion_evidence_candidates_path", "data/processed/mvp_d/expansion_evidence_candidates.jsonl"))
    rel_path = relevance_output_path or Path(output_cfg.get("expansion_domain_relevance_path", "data/processed/mvp_d/expansion_domain_relevance_scores.jsonl"))
    pain_path = pain_output_path or Path(output_cfg.get("expansion_pain_items_path", "data/processed/mvp_d/expansion_pain_items.jsonl"))
    candidates = _read_jsonl(cand_path)

    allowed_results, blocked_results = run_gate(candidates, int(cfg.get("gates", {}).get("require_raw_text_min_chars", 120)))
    build_gate_report(allowed_results, blocked_results, gate_report_path)
    allowed_ids = {item.candidate_id for item in allowed_results}
    allowed_candidates = [row for row in candidates if row.get("candidate_id") in allowed_ids]

    real_llm_run = llm_client is not None
    if llm_client is None and cfg.get("llm", {}).get("enabled", True):
        llm_client = None

    if not allowed_candidates:
        _write_jsonl(rel_path, [])
        _write_jsonl(pain_path, [])
        summary = {
            "real_llm_run": real_llm_run,
            "provider": getattr(llm_client, "provider", "none") if llm_client else "none",
            "model": getattr(llm_client, "model", "none") if llm_client else "none",
            "cache_enabled": use_cache,
            "total_candidates": len(candidates),
            "selected_for_llm": 0,
            "allowed_by_gate": len(allowed_results),
            "blocked_by_gate": len(blocked_results),
            "processed": 0,
            "should_extract_true": 0,
            "rejected": 0,
            "strong": 0,
            "medium": 0,
            "weak": 0,
            "failures": 0,
            "cache_hits": 0,
        }
        _write_report(summary, report_path)
        return [], [], summary

    relevance_results = run_domain_relevance_filter(
        allowed_candidates,
        llm_client=llm_client,
        use_llm_for_uncertain=real_llm_run,
        output_path=rel_path,
    )
    relevance_dicts = [item.model_dump() for item in relevance_results]

    pain_items = run_pain_extraction(
        allowed_candidates,
        relevance_dicts,
        llm_client=llm_client,
        max_items=max_items,
        output_path=pain_path,
    )
    pain_dicts = [item.model_dump() for item in pain_items]
    _write_jsonl(rel_path, relevance_results)
    _write_jsonl(pain_path, pain_items)

    strengths = Counter(item.get("evidence_strength") for item in pain_dicts)
    summary = {
        "real_llm_run": real_llm_run,
        "provider": getattr(llm_client, "provider", "none") if llm_client else "none",
        "model": getattr(llm_client, "model", "none") if llm_client else "none",
        "cache_enabled": use_cache,
        "total_candidates": len(candidates),
        "selected_for_llm": len(allowed_candidates),
        "allowed_by_gate": len(allowed_results),
        "blocked_by_gate": len(blocked_results),
        "processed": len(pain_dicts),
        "should_extract_true": sum(1 for item in pain_dicts if item.get("should_extract")),
        "rejected": sum(1 for item in pain_dicts if not item.get("should_extract")),
        "strong": strengths.get("strong", 0),
        "medium": strengths.get("medium", 0),
        "weak": strengths.get("weak", 0),
        "failures": sum(1 for item in pain_dicts if "failed" in str(item.get("reject_reason", "")).lower()),
        "cache_hits": sum(1 for item in pain_dicts if item.get("metadata", {}).get("cache_hit")),
    }
    _write_report(summary, report_path)
    return relevance_dicts, pain_dicts, summary


def _write_report(summary: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# MVP-D Expansion Pain Extraction Report",
        "",
        f"- real_llm_run: {str(summary['real_llm_run']).lower()}",
        f"- provider: {summary['provider']}",
        f"- model: {summary['model']}",
        f"- cache_enabled: {summary['cache_enabled']}",
        f"- total_candidates: {summary['total_candidates']}",
        f"- selected_for_llm: {summary['selected_for_llm']}",
        f"- allowed_by_gate: {summary['allowed_by_gate']}",
        f"- blocked_by_gate: {summary['blocked_by_gate']}",
        f"- processed: {summary['processed']}",
        f"- should_extract_true: {summary['should_extract_true']}",
        f"- rejected: {summary['rejected']}",
        f"- strong: {summary['strong']}",
        f"- medium: {summary['medium']}",
        f"- weak: {summary['weak']}",
        f"- failures: {summary['failures']}",
        f"- cache_hits: {summary['cache_hits']}",
    ]
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
