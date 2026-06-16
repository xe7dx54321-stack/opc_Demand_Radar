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
        engineering_acceptance="pass" if acquisition_summary["written_candidates"] >= 0 else "fail",
        product_acceptance="partial" if len(themes) < 2 else "pass",
        can_enter_second_review=len(themes) >= 2,
        can_enter_product_discovery=len(themes) >= 1 and extraction_summary["should_extract_true"] >= 8,
        reason="insufficient expansion evidence" if len(themes) < 2 else "seeded evidence expansion produced actionable themes",
        metadata={
            "radar_commit": _git_commit(),
            "foundation_commit": "unknown",
            "total_queries": total_queries,
            "provider": extraction_summary["provider"],
            "model": extraction_summary["model"],
            "real_llm_run": extraction_summary["real_llm_run"],
            "cache_enabled": extraction_summary["cache_enabled"],
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


def _write_run_summary(summary: MVPDRunSummary) -> None:
    out = Path("outputs/run_summary.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    if out.exists() and out.read_text(encoding="utf-8").strip():
        data = json.loads(out.read_text(encoding="utf-8"))
    data.update(summary.model_dump(mode="json"))
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
