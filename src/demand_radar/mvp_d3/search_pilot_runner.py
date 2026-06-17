"""MVP-D3: Search pilot runner."""
from __future__ import annotations
import json
from pathlib import Path
from demand_radar.mvp_d3.search_provider_client import make_search_client, detect_provider
from demand_radar.mvp_d3.search_query_selector import select_queries
from demand_radar.mvp_d3._impl import normalize_results, build_candidates, build_gate_report
from demand_radar.mvp_d.real_signal_gate import run_gate as mvp_d_run_gate
from demand_radar.mvp_b.pain_extraction_runner import run_pain_extraction


def run_search_pilot(max_queries: int = 24, max_results_per_query: int = 5,
                     use_cache: bool = True, llm_client=None,
                     fetch_pages: bool = True, output_dir: Path | None = None) -> dict:
    od = output_dir or Path("data/processed/mvp_d3")
    od.mkdir(parents=True, exist_ok=True)

    provider_name, api_key = detect_provider()
    if not provider_name:
        return {"status":"blocked","blocked_reason":"blocked_by_missing_search_provider",
                "provider":"none","total_search_results":0,"unique_urls":0,
                "evidence_candidates":0,"gate_allowed":0,"selected_for_llm":0,
                "should_extract_true":0,"pain_items":[],"normalized_results":[],
                "gate_allowed_results":[],"errors":[]}

    client = make_search_client(provider_name, api_key)
    selected = select_queries(max_queries=max_queries)
    if not selected:
        return {"status":"blocked","blocked_reason":"no_queries_selected",
                "provider":provider_name,"total_search_results":0,"unique_urls":0,
                "evidence_candidates":0,"gate_allowed":0,"selected_for_llm":0,
                "should_extract_true":0,"pain_items":[],"normalized_results":[],
                "gate_allowed_results":[],"errors":[]}

    all_results, errors = [], []
    for sq in selected:
        try:
            results = client.search(sq.query, max_results=max_results_per_query,
                                    query_id=sq.query_id, seed_id=sq.seed_id,
                                    query_type=sq.query_type)
            all_results.extend(results)
        except Exception as exc:
            errors.append(f"query {sq.query_id}: {exc}")

    normalized = normalize_results(all_results, output_path=od/"search_results.jsonl")
    candidates = build_candidates(normalized, fetch_pages=fetch_pages,
                                  output_path=od/"search_evidence_candidates.jsonl")
    cand_dicts = [json.loads(c.model_dump_json()) for c in candidates]
    gate_ok_results, gate_blocked_results = mvp_d_run_gate(cand_dicts)
    allowed_ids = {r.candidate_id for r in gate_ok_results}
    allowed_dicts = [c for c in cand_dicts if c["candidate_id"] in allowed_ids]

    gate_out = od/"search_gate_results.jsonl"
    gate_out.parent.mkdir(parents=True, exist_ok=True)
    with gate_out.open("w", encoding="utf-8") as f:
        for r in gate_ok_results + gate_blocked_results:
            f.write(r.model_dump_json() + "\n")
    build_gate_report(gate_ok_results, gate_blocked_results,
                      Path("outputs/mvp_d3/search_gate_report.md"))

    snippet_only = sum(1 for c in allowed_dicts
                       if (c.get("metadata") or {}).get("raw_text_source") == "snippet_only")
    full_page = len(allowed_dicts) - snippet_only

    rel_results = [{"candidate_id": c["candidate_id"], "relevance_decision": "include",
                    "relevance_score": 0.65} for c in allowed_dicts]
    pain_items, real_llm_run = [], False
    if llm_client and allowed_dicts:
        pain_items = run_pain_extraction(allowed_dicts, rel_results, llm_client=llm_client,
                                         output_path=od/"search_pain_items.jsonl")
        real_llm_run = True
    else:
        (od/"search_pain_items.jsonl").write_text("", encoding="utf-8")

    should_ext = sum(1 for p in pain_items if p.should_extract)
    return {
        "status":"ok","provider":provider_name,
        "model": getattr(llm_client,"model","none") if llm_client else "none",
        "real_llm_run":real_llm_run, "selected_queries":len(selected),
        "total_search_results":len(all_results), "unique_urls":len(normalized),
        "evidence_candidates":len(candidates), "gate_allowed":len(gate_ok_results),
        "gate_blocked":len(gate_blocked_results), "snippet_only_count":snippet_only,
        "full_page_count":full_page, "selected_for_llm":len(pain_items),
        "should_extract_true":should_ext,
        "strong": sum(1 for p in pain_items if p.evidence_strength=="strong"),
        "medium": sum(1 for p in pain_items if p.evidence_strength=="medium"),
        "weak":   sum(1 for p in pain_items if p.evidence_strength=="weak"),
        "failures":len(errors), "errors":errors, "pain_items":pain_items,
        "normalized_results":normalized, "gate_allowed_results":gate_ok_results,
    }
