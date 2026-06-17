"""MVP-D3: Pipeline orchestrator."""
from __future__ import annotations
import subprocess
from pathlib import Path
from demand_radar.mvp_d3.search_provider_schema import MVP_D3_RunSummary
from demand_radar.mvp_d3.search_pilot_runner import run_search_pilot
from demand_radar.mvp_d3._impl import analyze_yield, build_summary_report
from demand_radar.state.raw_store import utc_now_iso


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git","rev-parse","--short","HEAD"],text=True).strip()
    except Exception:
        return "unknown"


def run_mvp_d3(domain_id: str = "ai_investment_tracking",
               max_queries: int = 24, max_results_per_query: int = 5,
               use_cache: bool = True, llm_client=None,
               fetch_pages: bool = True) -> MVP_D3_RunSummary:
    now = utc_now_iso()
    commit = _git_commit()

    pilot = run_search_pilot(max_queries=max_queries,
                             max_results_per_query=max_results_per_query,
                             use_cache=use_cache, llm_client=llm_client,
                             fetch_pages=fetch_pages)

    analyze_yield([], pilot.get("normalized_results",[]),
                  pilot.get("gate_allowed_results",[]),
                  pilot.get("pain_items",[]),
                  output_path=Path("outputs/mvp_d3/search_yield_report.md"))

    build_summary_report(pilot, output_path=Path("outputs/mvp_d3/mvp_d3_summary_report.md"))

    blocked = pilot.get("blocked_reason")
    gate_ok = pilot.get("gate_allowed", 0)
    should_ext = pilot.get("should_extract_true", 0)
    sel_llm = pilot.get("selected_for_llm", 0)
    yield_rate = should_ext / sel_llm if sel_llm > 0 else 0.0
    eng = "partial" if (blocked or gate_ok == 0) else "pass"
    prod = "blocked" if blocked else ("pass" if should_ext >= 5 else
                                      "partial" if should_ext > 0 else "blocked")

    return MVP_D3_RunSummary(
        generated_at=now, radar_commit=commit,
        provider=pilot.get("provider","none"), model=pilot.get("model","none"),
        real_llm_run=pilot.get("real_llm_run",False),
        provider_available=(not blocked),
        blocked_reason=blocked,
        total_v2_queries=48, selected_queries=pilot.get("selected_queries",0),
        total_search_results=pilot.get("total_search_results",0),
        unique_urls=pilot.get("unique_urls",0),
        evidence_candidates=pilot.get("evidence_candidates",0),
        gate_allowed=gate_ok, gate_blocked=pilot.get("gate_blocked",0),
        snippet_only_count=pilot.get("snippet_only_count",0),
        full_page_count=pilot.get("full_page_count",0),
        selected_for_llm=sel_llm, should_extract_true=should_ext,
        strong=pilot.get("strong",0), medium=pilot.get("medium",0),
        weak=pilot.get("weak",0), failures=pilot.get("failures",0),
        yield_rate=yield_rate, engineering_acceptance=eng,
        product_acceptance=prod,
        can_enter_second_review=(should_ext >= 3),
        can_enter_foundation_source_upgrade=(blocked is not None),
        reason=blocked or f"yield_rate={yield_rate:.2%}",
        errors=pilot.get("errors",[]),
    )
