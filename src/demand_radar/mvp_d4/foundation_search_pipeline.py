"""MVP-D4: Foundation search pipeline."""
from __future__ import annotations
import json, subprocess
from pathlib import Path
from pydantic import BaseModel
from demand_radar.state.raw_store import utc_now_iso
from demand_radar.mvp_d4.foundation_search_adapter import (
    check_foundation_version, get_registry, detect_provider,
    run_foundation_search,
)
from demand_radar.mvp_d4.query_selector import select_queries
from demand_radar.mvp_d4.search_result_mapper import map_results
from demand_radar.mvp_d4.evidence_candidate_builder import build_candidates
from demand_radar.mvp_d4.yield_analyzer import analyze_yield
from demand_radar.mvp_d4.mvp_d4_report import build_gate_report, build_summary_report
from demand_radar.mvp_d.real_signal_gate import run_gate as radar_run_gate
from demand_radar.mvp_b.pain_extraction_runner import run_pain_extraction


def _gc():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True
        ).strip()
    except Exception:
        return "unknown"


class MVP_D4_RunSummary(BaseModel):
    generated_at: str
    radar_commit: str = "unknown"
    foundation_version: str = "0.1.2"
    foundation_commit: str = "b6d3497"
    provider: str = "none"
    model: str = "none"
    real_llm_run: bool = False
    provider_available: bool = False
    blocked_reason: str | None = None
    selected_queries: int = 0
    total_search_results: int = 0
    unique_urls: int = 0
    evidence_candidates: int = 0
    gate_allowed: int = 0
    gate_blocked: int = 0
    snippet_only_count: int = 0
    full_page_count: int = 0
    selected_for_llm: int = 0
    should_extract_true: int = 0
    strong: int = 0
    medium: int = 0
    weak: int = 0
    failures: int = 0
    yield_rate: float = 0.0
    engineering_acceptance: str = "partial"
    product_acceptance: str = "blocked"
    can_enter_second_review: bool = False
    can_enter_foundation_source_upgrade: bool = False
    reason: str = ""
    errors: list[str] = []


def run_mvp_d4(
    domain_id: str = "ai_investment_tracking",
    max_queries: int = 24,
    max_results_per_query: int = 5,
    use_cache: bool = True,
    llm_client=None,
) -> MVP_D4_RunSummary:
    now = utc_now_iso()
    commit = _gc()
    od = Path("data/processed/mvp_d4")
    od.mkdir(parents=True, exist_ok=True)

    ver_ok, ver_str = check_foundation_version()
    if not ver_ok:
        return MVP_D4_RunSummary(
            generated_at=now, radar_commit=commit,
            blocked_reason=f"foundation_version_insufficient:{ver_str}",
            reason=f"foundation_version_insufficient:{ver_str}",
        )

    try:
        registry = get_registry()
        provider_name = detect_provider(registry)
    except Exception:
        provider_name = None

    if not provider_name:
        summary = MVP_D4_RunSummary(
            generated_at=now, radar_commit=commit, foundation_version=ver_str,
            blocked_reason="blocked_by_missing_search_provider",
            reason="blocked_by_missing_search_provider",
        )
        build_summary_report(
            summary.model_dump(), Path("outputs/mvp_d4/mvp_d4_summary_report.md")
        )
        return summary

    selected = select_queries(max_queries=max_queries)
    if not selected:
        return MVP_D4_RunSummary(
            generated_at=now, radar_commit=commit, foundation_version=ver_str,
            provider=provider_name, provider_available=True,
            blocked_reason="no_queries_selected", reason="no_queries_selected",
        )

    all_mapped: list[dict] = []
    errors: list[str] = []
    results_out = od / "foundation_search_results.jsonl"
    results_out.write_text("", encoding="utf-8")
    for q in selected:
        try:
            foundation_results = run_foundation_search(
                q.get("query", ""), max_results=max_results_per_query, registry=registry
            )
            mapped = map_results(foundation_results, query_meta=q, output_path=results_out)
            all_mapped.extend(mapped)
        except Exception as exc:
            errors.append(f"query {q.get('query_id', '?')}: {exc}")

    unique_urls = len({r.get("url", "") for r in all_mapped})
    candidates = build_candidates(
        all_mapped, use_foundation_extraction=True,
        output_path=od / "foundation_search_evidence_candidates.jsonl",
    )

    cand_dicts = [json.loads(c.model_dump_json()) for c in candidates]
    gate_ok_list, gate_blocked_list = radar_run_gate(cand_dicts)
    allowed_ids = {r.candidate_id for r in gate_ok_list}
    allowed_dicts = [c for c in cand_dicts if c["candidate_id"] in allowed_ids]

    build_gate_report(
        gate_ok_list, gate_blocked_list,
        Path("outputs/mvp_d4/foundation_search_gate_report.md"),
    )
    gate_out = od / "foundation_search_gate_results.jsonl"
    with gate_out.open("w", encoding="utf-8") as gf:
        for r in gate_ok_list + gate_blocked_list:
            gf.write(r.model_dump_json() + chr(10))

    snippet_only = sum(
        1 for c in allowed_dicts
        if (c.get("metadata") or {}).get("raw_text_source") == "snippet_only"
    )
    full_page = len(allowed_dicts) - snippet_only

    rel_results = [
        {"candidate_id": c["candidate_id"], "relevance_decision": "include",
         "relevance_score": 0.65}
        for c in allowed_dicts
    ]
    pain_items = []
    real_llm_run = False
    if llm_client and allowed_dicts:
        pain_items = run_pain_extraction(
            allowed_dicts, rel_results, llm_client=llm_client,
            output_path=od / "foundation_search_pain_items.jsonl",
        )
        real_llm_run = True
    else:
        (od / "foundation_search_pain_items.jsonl").write_text("", encoding="utf-8")

    yield_metrics = analyze_yield(
        selected, all_mapped, gate_ok_list, pain_items,
        output_path=Path("outputs/mvp_d4/foundation_search_yield_report.md"),
    )

    should_ext = yield_metrics["should_extract_true"]
    sel_llm = yield_metrics["selected_for_llm"]
    yield_rate = yield_metrics["yield_rate"]
    model_name = getattr(llm_client, "model", "none") if llm_client else "none"
    eng = "pass" if real_llm_run else "partial"
    prod = (
        "pass" if should_ext >= 5
        else "partial" if should_ext > 0
        else "blocked"
    )

    pilot_dict = {
        "provider": provider_name, "model": model_name,
        "real_llm_run": real_llm_run, "selected_queries": len(selected),
        "total_search_results": len(all_mapped), "unique_urls": unique_urls,
        "evidence_candidates": len(candidates),
        "gate_allowed": len(gate_ok_list), "gate_blocked": len(gate_blocked_list),
        "snippet_only_count": snippet_only, "full_page_count": full_page,
        "selected_for_llm": sel_llm, "should_extract_true": should_ext,
        "strong": yield_metrics["strong"], "medium": yield_metrics["medium"],
        "weak": yield_metrics["weak"], "failures": len(errors),
        "errors": errors, "pain_items": pain_items,
    }
    build_summary_report(pilot_dict, Path("outputs/mvp_d4/mvp_d4_summary_report.md"))

    return MVP_D4_RunSummary(
        generated_at=now, radar_commit=commit, foundation_version=ver_str,
        provider=provider_name, model=model_name, real_llm_run=real_llm_run,
        provider_available=True, selected_queries=len(selected),
        total_search_results=len(all_mapped), unique_urls=unique_urls,
        evidence_candidates=len(candidates), gate_allowed=len(gate_ok_list),
        gate_blocked=len(gate_blocked_list), snippet_only_count=snippet_only,
        full_page_count=full_page, selected_for_llm=sel_llm,
        should_extract_true=should_ext, strong=yield_metrics["strong"],
        medium=yield_metrics["medium"], weak=yield_metrics["weak"],
        failures=len(errors), yield_rate=yield_rate,
        engineering_acceptance=eng, product_acceptance=prod,
        can_enter_second_review=(should_ext >= 3),
        reason=f"yield_rate={yield_rate:.2%}", errors=errors,
    )
