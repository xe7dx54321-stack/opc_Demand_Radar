"""MVP-D seeded evidence expansion pipeline."""
from __future__ import annotations

import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

from demand_radar.mvp_d.evidence_consolidator import consolidate_evidence
from demand_radar.mvp_d.expansion_extraction import run_expansion_extraction
from demand_radar.mvp_d.mvp_d_report import build_mvp_d_summary_report
from demand_radar.mvp_d.query_generator import generate_queries
from demand_radar.mvp_d.seed_selector import select_seeds
from demand_radar.mvp_d.seed_schema import MVPDRunSummary
from demand_radar.mvp_d.seeded_acquisition import run_seeded_acquisition
from demand_radar.mvp_d.theme_grouping import build_demand_themes
from demand_radar.state.raw_store import utc_now_iso


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def run_mvp_d(
    domain_id: str = "ai_investment_tracking",
    use_cache: bool = True,
    max_seeds: int | None = None,
    max_queries: int | None = None,
    max_results: int | None = None,
) -> MVPDRunSummary:
    cfg_path = Path("configs/seeded_expansion_config.yaml")
    seed_profiles, seed_summary = select_seeds(
        config_path=cfg_path,
        output_path=None,
        max_seeds_override=max_seeds,
    )

    query_plan = generate_queries(
        seed_profiles,
        config_path=cfg_path,
        max_queries_total=max_queries,
    )

    acquisition_rows, acquisition_summary = run_seeded_acquisition(
        config_path=cfg_path,
        max_queries=max_queries,
        max_results=max_results,
    )
    relevance_rows, pain_rows, extraction_summary = run_expansion_extraction(
        config_path=cfg_path,
        max_items=max_results,
        use_cache=use_cache,
    )
    consolidations = consolidate_evidence(config_path=cfg_path)
    themes = build_demand_themes(
        Path("data/processed/mvp_d/seed_profiles.jsonl"),
        Path("data/processed/mvp_d/seed_evidence_consolidation.jsonl"),
        Path("data/processed/mvp_d/consolidated_evidence_themes.jsonl"),
        Path("outputs/mvp_d/demand_theme_grouping_report.md"),
    )

    total_queries = len(query_plan)
    queries_by_seed = Counter(query.seed_id for query in query_plan)
    queries_by_connector = Counter(query.connector for query in query_plan)
    selected_seed_ids = [seed.seed_id for seed in seed_profiles]
    top_themes = [
        {
            "theme_title_zh": theme.theme_title_zh,
            "recommendation": theme.action_recommendation,
            "evidence_count": theme.evidence_count,
        }
        for theme in themes[:5]
    ]

    engineering_acceptance, product_acceptance, can_enter_second_review, can_enter_product_discovery, reason = _acceptance_from_outputs(
        extraction_summary=extraction_summary,
        themes_count=len(themes),
        consolidations=consolidations,
    )

    summary = MVPDRunSummary(
        domain_id=domain_id,
        generated_at=utc_now_iso(),
        total_reviews=seed_summary.total_reviews,
        eligible_seeds=seed_summary.eligible_seeds,
        optional_seeds=seed_summary.optional_seeds,
        excluded_reviews=seed_summary.excluded_reviews,
        total_queries=total_queries,
        raw_new_signals=acquisition_summary["raw_new_signals"],
        unique_new_signals=acquisition_summary["unique_new_signals"],
        deduped_against_existing=acquisition_summary["deduped_against_existing"],
        allowed_by_gate=acquisition_summary["allowed_by_gate"],
        blocked_by_gate=acquisition_summary["blocked_by_gate"],
        selected_for_llm=extraction_summary["selected_for_llm"],
        expansion_pain_items=len(pain_rows),
        should_extract_true=extraction_summary["should_extract_true"],
        themes=len(themes),
        engineering_acceptance=engineering_acceptance,
        product_acceptance=product_acceptance,
        can_enter_second_review=can_enter_second_review,
        can_enter_product_discovery=can_enter_product_discovery,
        reason=reason,
        metadata={
            "radar_commit": _git_commit(),
            "foundation_commit": "unknown",
            "total_queries": total_queries,
            "provider": extraction_summary["provider"],
            "model": extraction_summary["model"],
            "real_llm_run": extraction_summary["real_llm_run"],
            "cache_enabled": extraction_summary["cache_enabled"],
            "status": extraction_summary.get("status", "completed"),
            "blocked_reason": extraction_summary.get("blocked_reason"),
            "prompt_version": extraction_summary.get("prompt_version"),
            "run_scope": extraction_summary.get("run_scope"),
            "selected_seed_ids": selected_seed_ids,
            "queries_by_seed": dict(queries_by_seed),
            "queries_by_connector": dict(queries_by_connector),
            "query_examples": [query.query for query in query_plan[:5]],
            "source_url_present": acquisition_summary["source_url_present"],
            "strong": extraction_summary["strong"],
            "medium": extraction_summary["medium"],
            "weak": extraction_summary["weak"],
            "failures": extraction_summary["failures"],
            "cache_hits": extraction_summary["cache_hits"],
            "seeds_with_new_support": sum(1 for item in consolidations if item.new_extracted_pain_count > 0),
            "seeds_without_new_support": sum(1 for item in consolidations if item.new_extracted_pain_count == 0),
            "pursue_candidate": sum(1 for item in consolidations if item.recommendation == "pursue_candidate"),
            "watch": sum(1 for item in consolidations if item.recommendation == "watch"),
            "needs_more_evidence": sum(1 for item in consolidations if item.recommendation == "needs_more_evidence"),
            "reject": sum(1 for item in consolidations if item.recommendation == "reject"),
            "top_themes": top_themes,
        },
    )
    build_mvp_d_summary_report(summary, metadata=summary.metadata)
    _write_run_summary(summary)
    return summary


def build_mvp_d_summary_from_stored(
    domain_id: str = "ai_investment_tracking",
) -> MVPDRunSummary:
    seed_selection_summary = _read_markdown_kv_report(Path("outputs/mvp_d/seed_selection_report.md"))
    seed_rows = _read_jsonl(Path("data/processed/mvp_d/seed_profiles.jsonl"))
    query_rows = _read_jsonl(Path("data/processed/mvp_d/seeded_query_plan.jsonl"))
    candidate_rows = _read_jsonl(Path("data/processed/mvp_d/expansion_evidence_candidates.jsonl"))
    pain_rows = _read_jsonl(Path("data/processed/mvp_d/expansion_pain_items.jsonl"))
    consolidation_rows = _read_jsonl(Path("data/processed/mvp_d/seed_evidence_consolidation.jsonl"))
    theme_rows = _read_jsonl(Path("data/processed/mvp_d/consolidated_evidence_themes.jsonl"))
    extraction_summary = _read_extraction_summary_from_report(
        Path("outputs/mvp_d/expansion_pain_extraction_report.md"),
        pain_rows,
        candidate_rows,
    )
    acquisition_summary = _read_acquisition_summary_from_report(Path("outputs/mvp_d/seeded_acquisition_report.md"))
    allowed_by_gate = int(extraction_summary.get("allowed_by_gate", acquisition_summary.get("allowed_by_gate", 0)))
    blocked_by_gate = int(extraction_summary.get("blocked_by_gate", acquisition_summary.get("blocked_by_gate", 0)))
    queries_by_seed = Counter(row.get("seed_id") for row in query_rows)
    queries_by_connector = Counter(row.get("connector") for row in query_rows)
    top_themes = [
        {
            "theme_title_zh": theme.get("theme_title_zh"),
            "recommendation": theme.get("action_recommendation"),
            "evidence_count": theme.get("evidence_count"),
        }
        for theme in theme_rows[:5]
    ]
    engineering_acceptance, product_acceptance, can_enter_second_review, can_enter_product_discovery, reason = _acceptance_from_outputs(
        extraction_summary=extraction_summary,
        themes_count=len(theme_rows),
        consolidations=consolidation_rows,
    )
    summary = MVPDRunSummary(
        domain_id=domain_id,
        generated_at=str(extraction_summary.get("generated_at", utc_now_iso())),
        total_reviews=int(seed_selection_summary.get("total_reviews", len(seed_rows))),
        eligible_seeds=int(seed_selection_summary.get("eligible_seeds", sum(1 for row in seed_rows if row.get("true_pain") is True))),
        optional_seeds=int(seed_selection_summary.get("optional_seeds", sum(1 for row in seed_rows if row.get("expansion_priority") == "low"))),
        excluded_reviews=int(seed_selection_summary.get("excluded_reviews", 0)),
        total_queries=len(query_rows),
        raw_new_signals=int(acquisition_summary.get("raw_new_signals", len(candidate_rows))),
        unique_new_signals=int(acquisition_summary.get("unique_new_signals", len(candidate_rows))),
        deduped_against_existing=int(acquisition_summary.get("deduped_against_existing", 0)),
        allowed_by_gate=allowed_by_gate,
        blocked_by_gate=blocked_by_gate,
        selected_for_llm=int(extraction_summary.get("selected_for_llm", 0)),
        expansion_pain_items=len(pain_rows),
        should_extract_true=int(extraction_summary.get("should_extract_true", 0)),
        themes=len(theme_rows),
        engineering_acceptance=engineering_acceptance,
        product_acceptance=product_acceptance,
        can_enter_second_review=can_enter_second_review,
        can_enter_product_discovery=can_enter_product_discovery,
        reason=reason,
        metadata={
            "radar_commit": _git_commit(),
            "foundation_commit": "unknown",
            "total_queries": len(query_rows),
            "provider": extraction_summary.get("provider", "none"),
            "model": extraction_summary.get("model", "none"),
            "real_llm_run": extraction_summary.get("real_llm_run", False),
            "cache_enabled": extraction_summary.get("cache_enabled", False),
            "status": extraction_summary.get("status", "completed"),
            "blocked_reason": extraction_summary.get("blocked_reason"),
            "prompt_version": extraction_summary.get("prompt_version"),
            "run_scope": extraction_summary.get("run_scope"),
            "selected_seed_ids": seed_selection_summary.get("selected_seed_ids", [row.get("seed_id") for row in seed_rows]),
            "queries_by_seed": dict(queries_by_seed),
            "queries_by_connector": dict(queries_by_connector),
            "query_examples": [row.get("query") for row in query_rows[:5]],
            "source_url_present": int(acquisition_summary.get("source_url_present", sum(1 for row in candidate_rows if row.get("source_url")))),
            "strong": int(extraction_summary.get("strong", 0)),
            "medium": int(extraction_summary.get("medium", 0)),
            "weak": int(extraction_summary.get("weak", 0)),
            "failures": int(extraction_summary.get("failures", 0)),
            "cache_hits": int(extraction_summary.get("cache_hits", 0)),
            "seeds_with_new_support": sum(1 for row in consolidation_rows if int(row.get("new_extracted_pain_count", 0)) > 0),
            "seeds_without_new_support": sum(1 for row in consolidation_rows if int(row.get("new_extracted_pain_count", 0)) == 0),
            "pursue_candidate": sum(1 for row in consolidation_rows if row.get("recommendation") == "pursue_candidate"),
            "watch": sum(1 for row in consolidation_rows if row.get("recommendation") == "watch"),
            "needs_more_evidence": sum(1 for row in consolidation_rows if row.get("recommendation") == "needs_more_evidence"),
            "reject": sum(1 for row in consolidation_rows if row.get("recommendation") == "reject"),
            "top_themes": top_themes,
        },
    )
    build_mvp_d_summary_report(summary, metadata=summary.metadata)
    _write_run_summary(summary)
    return summary


def _write_run_summary(summary: MVPDRunSummary) -> None:
    out = Path("outputs/run_summary.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    if out.exists() and out.read_text(encoding="utf-8").strip():
        data = json.loads(out.read_text(encoding="utf-8"))
    data.update(summary.model_dump(mode="json"))
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _acceptance_from_outputs(
    extraction_summary: dict[str, Any],
    themes_count: int,
    consolidations: list[Any],
) -> tuple[str, str, bool, bool, str]:
    if extraction_summary.get("status") == "blocked" or not extraction_summary.get("real_llm_run"):
        reason = extraction_summary.get("blocked_reason") or "real LLM extraction not executed"
        return "blocked", "blocked", False, False, reason
    engineering_ok = (
        int(extraction_summary.get("selected_for_llm", 0)) > 0
        and int(extraction_summary.get("processed", 0)) > 0
        and str(extraction_summary.get("provider", "none")) not in {"none", ""}
        and str(extraction_summary.get("model", "none")) not in {"none", ""}
    )
    seeds_with_two = sum(
        1
        for item in consolidations
        if _consolidation_count(item) >= 2
    )
    strong_medium = int(extraction_summary.get("strong", 0)) + int(extraction_summary.get("medium", 0))
    should_extract_true = int(extraction_summary.get("should_extract_true", 0))
    product_ok = should_extract_true >= 5 and strong_medium >= 3 and seeds_with_two >= 2 and themes_count >= 1
    if engineering_ok and product_ok:
        return "pass", "pass", True, True, "real LLM expansion produced enough supporting evidence"
    if engineering_ok:
        return "pass", "partial", True, False, "real LLM ran but expansion evidence is still limited"
    return "partial", "blocked", False, False, "real LLM extraction did not reach engineering acceptance"


def _consolidation_count(item: Any) -> int:
    if isinstance(item, dict):
        return int(item.get("new_extracted_pain_count", 0))
    return int(getattr(item, "new_extracted_pain_count", 0))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _read_markdown_kv_report(path: Path) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    if not path.exists():
        return summary
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text.startswith("- ") or ":" not in text:
            continue
        key, value = text[2:].split(":", 1)
        value = value.strip()
        if value.lower() in {"true", "false"}:
            summary[key.strip()] = value.lower() == "true"
            continue
        try:
            summary[key.strip()] = int(value)
            continue
        except ValueError:
            pass
        try:
            summary[key.strip()] = json.loads(value)
        except Exception:
            summary[key.strip()] = None if value == "n/a" else value
    return summary


def _read_extraction_summary_from_report(
    path: Path,
    pain_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "status": "completed",
        "real_llm_run": False,
        "provider": "none",
        "model": "none",
        "cache_enabled": False,
        "selected_for_llm": len(candidate_rows),
        "allowed_by_gate": len(candidate_rows),
        "blocked_by_gate": 0,
        "processed": len(pain_rows),
        "should_extract_true": sum(1 for row in pain_rows if row.get("should_extract")),
        "strong": sum(1 for row in pain_rows if row.get("evidence_strength") == "strong"),
        "medium": sum(1 for row in pain_rows if row.get("evidence_strength") == "medium"),
        "weak": sum(1 for row in pain_rows if row.get("evidence_strength") == "weak"),
        "failures": sum(1 for row in pain_rows if "failed" in str(row.get("reject_reason", "")).lower()),
        "cache_hits": sum(1 for row in pain_rows if (row.get("metadata") or {}).get("cache_hit")),
    }
    if not path.exists():
        return summary
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text.startswith("- ") or ":" not in text:
            continue
        key, value = text[2:].split(":", 1)
        value = value.strip()
        if value.lower() in {"true", "false"}:
            summary[key.strip()] = value.lower() == "true"
        else:
            try:
                summary[key.strip()] = int(value)
            except ValueError:
                summary[key.strip()] = None if value == "n/a" else value
    return summary


def _read_acquisition_summary_from_report(path: Path) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    if not path.exists():
        return summary
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text.startswith("- ") or ":" not in text:
            continue
        key, value = text[2:].split(":", 1)
        value = value.strip()
        try:
            summary[key.strip()] = int(value)
        except ValueError:
            summary[key.strip()] = value
    return summary
