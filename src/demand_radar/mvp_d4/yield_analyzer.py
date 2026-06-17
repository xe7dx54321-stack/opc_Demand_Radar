"""MVP-D4: Search yield analysis."""
from __future__ import annotations
from collections import Counter
from pathlib import Path


def analyze_yield(
    selected_queries: list,
    mapped_results: list[dict],
    gate_allowed: list,
    pain_items: list,
    output_path: Path | None = None,
) -> dict:
    extracted = [p for p in pain_items if getattr(p, "should_extract", False)]
    sel_llm = len(pain_items)
    yield_rate = len(extracted) / sel_llm if sel_llm > 0 else 0.0
    strong = sum(1 for p in pain_items if getattr(p, "evidence_strength","") == "strong")
    medium = sum(1 for p in pain_items if getattr(p, "evidence_strength","") == "medium")
    weak   = sum(1 for p in pain_items if getattr(p, "evidence_strength","") == "weak")
    qt_r  = Counter(r.get("query_type","unknown") for r in mapped_results)
    seed_r = Counter(r.get("seed_id","unknown") for r in mapped_results)
    dom_r  = Counter(r.get("result_domain","unknown") for r in mapped_results)
    # gate_allowed contains GateResult objects; raw_text_source is not available here
    src_r: Counter = Counter({"unknown": len(gate_allowed)})
    lines = ["# MVP-D4 Foundation Search Yield Report\n",
             f"- selected_queries: {len(selected_queries)}",
             f"- search_results: {len(mapped_results)}",
             f"- unique_urls: {len({r.get('url','') for r in mapped_results})}",
             f"- gate_allowed: {len(gate_allowed)}",
             f"- selected_for_llm: {sel_llm}",
             f"- should_extract_true: {len(extracted)}",
             f"- strong: {strong}", f"- medium: {medium}", f"- weak: {weak}",
             f"- yield_rate: {yield_rate:.2%}",
             "\n## By Query Type"] + [f"- {k}: {v}" for k,v in qt_r.most_common()] + \
            ["\n## By Seed"] + [f"- {k}: {v}" for k,v in seed_r.most_common()] + \
            ["\n## By Result Domain (top 10)"] + [f"- {k}: {v}" for k,v in dom_r.most_common(10)] + \
            ["\n## By Raw Text Source"] + [f"- {k}: {v}" for k,v in src_r.most_common()]
    report = "\n".join(lines) + "\n"
    op = output_path or Path("outputs/mvp_d4/foundation_search_yield_report.md")
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(report, encoding="utf-8")
    return {
        "total_queries": len(selected_queries),
        "search_results": len(mapped_results),
        "unique_urls": len({r.get("url","") for r in mapped_results}),
        "gate_allowed": len(gate_allowed),
        "selected_for_llm": sel_llm,
        "should_extract_true": len(extracted),
        "strong": strong, "medium": medium, "weak": weak,
        "yield_rate": yield_rate,
        "by_query_type": dict(qt_r.most_common()),
        "by_seed": dict(seed_r.most_common()),
        "by_domain": dict(dom_r.most_common(10)),
        "by_raw_text_source": dict(src_r.most_common()),
    }
