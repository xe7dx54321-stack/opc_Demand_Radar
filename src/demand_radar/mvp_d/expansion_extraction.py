"""MVP-D expansion domain relevance and pain extraction."""
from __future__ import annotations

import json
import os
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from demand_radar.mvp_b.domain_relevance_filter import run_domain_relevance_filter
from demand_radar.mvp_b.pain_extraction_runner import run_pain_extraction
from demand_radar.mvp_d.llm_cache import MVPDPainExtractionCache
from demand_radar.mvp_d.real_signal_gate import build_gate_report, run_gate
from demand_radar.semantic_merge.llm_client import make_llm_client
from demand_radar.state.raw_store import utc_now_iso

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


def _load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _env_first(*keys: str) -> tuple[str | None, str | None]:
    for key in keys:
        if key and os.environ.get(key):
            return key, os.environ[key]
    return None, None


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def _llm_settings(cfg: dict[str, Any]) -> dict[str, Any]:
    llm_cfg = cfg.get("llm", {})
    provider_env = str(llm_cfg.get("provider_env", "LLM_PROVIDER"))
    model_env = str(llm_cfg.get("model_env", "LLM_MODEL"))
    provider = (
        os.environ.get("DEMAND_RADAR_LLM_PROVIDER")
        or os.environ.get(provider_env)
        or str(llm_cfg.get("default_provider", "responses_compatible"))
    )
    model = (
        os.environ.get("DEMAND_RADAR_LLM_MODEL")
        or os.environ.get(model_env)
        or str(llm_cfg.get("default_model", "claude-sonnet-4-6"))
    )
    base_url_env, base_url = _env_first(
        str(llm_cfg.get("base_url_env", "DEMAND_RADAR_LLM_BASE_URL")),
        "DEMAND_RADAR_LLM_BASE_URL",
        "LLM_BASE_URL",
    )
    api_key_env, api_key = _env_first(
        str(llm_cfg.get("api_key_env", "DEMAND_RADAR_LLM_API_KEY")),
        "DEMAND_RADAR_LLM_API_KEY",
        "LLM_API_KEY",
    )
    return {
        "enabled": bool(llm_cfg.get("enabled", True)),
        "provider": provider,
        "model": model,
        "base_url_env": base_url_env or "DEMAND_RADAR_LLM_BASE_URL",
        "api_key_env": api_key_env or "DEMAND_RADAR_LLM_API_KEY",
        "base_url_present": bool(base_url),
        "api_key_present": bool(api_key),
        "temperature": float(llm_cfg.get("temperature", 0)),
        "max_tokens": int(llm_cfg.get("max_tokens", 4000)),
        "cache_enabled": bool(llm_cfg.get("cache_enabled", True)),
        "prompt_version": str(llm_cfg.get("prompt_version", "acquired_signal_pain_extraction_v1")),
        "run_scope": str(llm_cfg.get("run_scope", "demand_radar_mvp_d_seeded_expansion")),
    }


def _build_default_llm_client(cfg: dict[str, Any]):
    _load_dotenv()
    settings = _llm_settings(cfg)
    if not settings["enabled"]:
        return None, settings, "llm_disabled"
    missing: list[str] = []
    if not settings["base_url_present"]:
        missing.append(settings["base_url_env"])
    if not settings["api_key_present"]:
        missing.append(settings["api_key_env"])
    if not settings["model"]:
        missing.append("model")
    if missing:
        return None, settings, "missing_llm_config:" + ",".join(missing)
    client = make_llm_client(
        settings["provider"],
        {
            "llm": {
                "base_url_env": settings["base_url_env"],
                "api_key_env": settings["api_key_env"],
                "model": settings["model"],
                "temperature": settings["temperature"],
                "max_tokens": settings["max_tokens"],
            }
        },
    )
    return client, settings, None


def run_expansion_extraction(
    config_path: Path | None = None,
    candidates_path: Path | None = None,
    relevance_output_path: Path | None = None,
    pain_output_path: Path | None = None,
    gate_report_path: Path = Path("outputs/mvp_d/real_signal_gate_report.md"),
    report_path: Path = Path("outputs/mvp_d/expansion_pain_extraction_report.md"),
    llm_pass_report_path: Path = Path("outputs/mvp_d/mvp_d_llm_expansion_pass_report.md"),
    llm_client=None,
    max_items: int | None = None,
    use_cache: bool = True,
) -> tuple[list[dict], list[dict], dict[str, Any]]:
    cfg = _load_cfg(config_path)
    llm_settings = _llm_settings(cfg)
    output_cfg = cfg.get("output", {})
    cand_path = candidates_path or Path(output_cfg.get("expansion_evidence_candidates_path", "data/processed/mvp_d/expansion_evidence_candidates.jsonl"))
    rel_path = relevance_output_path or Path(output_cfg.get("expansion_domain_relevance_path", "data/processed/mvp_d/expansion_domain_relevance_scores.jsonl"))
    pain_path = pain_output_path or Path(output_cfg.get("expansion_pain_items_path", "data/processed/mvp_d/expansion_pain_items.jsonl"))
    candidates = _read_jsonl(cand_path)

    allowed_results, blocked_results = run_gate(candidates, int(cfg.get("gates", {}).get("require_raw_text_min_chars", 120)))
    build_gate_report(allowed_results, blocked_results, gate_report_path)
    allowed_ids = {item.candidate_id for item in allowed_results}
    allowed_candidates = [row for row in candidates if row.get("candidate_id") in allowed_ids]

    llm_block_reason = None
    if llm_client is None:
        llm_client, llm_settings, llm_block_reason = _build_default_llm_client(cfg)

    provider = getattr(llm_client, "provider", llm_settings.get("provider", "none")) if llm_client else llm_settings.get("provider", "none")
    model = getattr(llm_client, "model", llm_settings.get("model", "none")) if llm_client else llm_settings.get("model", "none")
    real_llm_run = llm_client is not None and provider not in {"fake", "none"}
    prompt_version = llm_settings.get("prompt_version", "acquired_signal_pain_extraction_v1")
    run_scope = llm_settings.get("run_scope", "demand_radar_mvp_d_seeded_expansion")

    if not allowed_candidates:
        _write_jsonl(rel_path, [])
        _write_jsonl(pain_path, [])
        summary = {
            "generated_at": utc_now_iso(),
            "radar_commit": _git_commit(),
            "foundation_commit": "unknown",
            "real_llm_run": real_llm_run,
            "provider": provider,
            "model": model,
            "cache_enabled": use_cache,
            "prompt_version": prompt_version,
            "run_scope": run_scope,
            "status": "blocked" if llm_block_reason else "no_candidates",
            "blocked_reason": llm_block_reason,
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
        _write_llm_pass_report(summary, report_path=llm_pass_report_path)
        return [], [], summary

    if llm_client is None:
        _write_jsonl(rel_path, [])
        _write_jsonl(pain_path, [])
        summary = {
            "generated_at": utc_now_iso(),
            "radar_commit": _git_commit(),
            "foundation_commit": "unknown",
            "real_llm_run": False,
            "provider": provider,
            "model": model,
            "cache_enabled": use_cache,
            "prompt_version": prompt_version,
            "run_scope": run_scope,
            "status": "blocked",
            "blocked_reason": llm_block_reason or "llm_client_unavailable",
            "total_candidates": len(candidates),
            "selected_for_llm": len(allowed_candidates),
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
        _write_llm_pass_report(summary, report_path=llm_pass_report_path)
        return [], [], summary

    relevance_results = run_domain_relevance_filter(
        allowed_candidates,
        llm_client=llm_client,
        use_llm_for_uncertain=real_llm_run,
        output_path=rel_path,
    )
    relevance_dicts = [item.model_dump() for item in relevance_results]
    cache = MVPDPainExtractionCache(enabled=bool(use_cache and llm_settings.get("cache_enabled", True)))

    pain_items = run_pain_extraction(
        allowed_candidates,
        relevance_dicts,
        llm_client=llm_client,
        max_items=max_items,
        output_path=pain_path,
        cache_backend=cache,
        prompt_version_override=prompt_version,
        run_scope_override=run_scope,
    )
    candidate_meta = {row.get("candidate_id"): row.get("metadata") or {} for row in allowed_candidates}
    for item in pain_items:
        meta = dict(item.metadata or {})
        source_meta = candidate_meta.get(item.candidate_id, {})
        for key in ("seed_id", "pain_item_id", "seed_query_id", "expansion_run_id", "expansion_source"):
            if source_meta.get(key) is not None:
                meta[key] = source_meta.get(key)
        meta.update(
            {
                "provider": provider,
                "model": model,
                "real_llm_run": real_llm_run,
                "prompt_version": prompt_version,
                "run_scope": run_scope,
            }
        )
        item.metadata = meta
    pain_dicts = [item.model_dump() for item in pain_items]
    _write_jsonl(rel_path, relevance_results)
    _write_jsonl(pain_path, pain_items)

    strengths = Counter(item.get("evidence_strength") for item in pain_dicts)
    summary = {
        "generated_at": utc_now_iso(),
        "radar_commit": _git_commit(),
        "foundation_commit": "unknown",
        "real_llm_run": real_llm_run,
        "provider": provider,
        "model": model,
        "cache_enabled": use_cache,
        "prompt_version": prompt_version,
        "run_scope": run_scope,
        "status": "completed",
        "blocked_reason": None,
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
        "stale_cache_prevented": cache.stats.stale_prevented,
    }
    _write_report(summary, report_path)
    _write_llm_pass_report(summary, pain_dicts, allowed_candidates, report_path=llm_pass_report_path)
    return relevance_dicts, pain_dicts, summary


def _write_report(summary: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# MVP-D Expansion Pain Extraction Report",
        "",
        f"- status: {summary.get('status', 'completed')}",
        f"- blocked_reason: {summary.get('blocked_reason') or 'n/a'}",
        f"- real_llm_run: {str(summary['real_llm_run']).lower()}",
        f"- provider: {summary['provider']}",
        f"- model: {summary['model']}",
        f"- cache_enabled: {summary['cache_enabled']}",
        f"- prompt_version: {summary.get('prompt_version', 'n/a')}",
        f"- run_scope: {summary.get('run_scope', 'n/a')}",
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
        f"- stale_cache_prevented: {summary.get('stale_cache_prevented', 0)}",
    ]
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _write_llm_pass_report(
    summary: dict[str, Any],
    pain_items: list[dict[str, Any]] | None = None,
    candidates: list[dict[str, Any]] | None = None,
    report_path: Path = Path("outputs/mvp_d/mvp_d_llm_expansion_pass_report.md"),
) -> None:
    from demand_radar.mvp_d.mvp_d_report import build_mvp_d_llm_expansion_pass_report

    build_mvp_d_llm_expansion_pass_report(
        extraction_summary=summary,
        pain_items=pain_items,
        candidates=candidates,
        report_path=report_path,
    )
