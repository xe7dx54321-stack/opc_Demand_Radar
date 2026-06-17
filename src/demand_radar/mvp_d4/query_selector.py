"""MVP-D4: Select calibrated queries for Foundation search."""
from __future__ import annotations
import json
from collections import defaultdict
from pathlib import Path
from demand_radar.state.raw_store import utc_now_iso

_V2_PATH = Path("data/processed/mvp_d2/calibrated_query_plan_v2.jsonl")
_OUT_PATH = Path("data/processed/mvp_d4/selected_foundation_search_queries.jsonl")
_PRIORITY_TYPES = ["manual_workflow","pain_phrase","spreadsheet_workaround",
                   "workaround_phrase","complaint_phrase","buying_intent"]


def select_queries(
    v2_path: Path | None = None,
    output_path: Path | None = None,
    max_queries: int = 24,
    max_per_seed: int = 6,
    report_path: Path | None = None,
) -> list[dict]:
    src = v2_path or _V2_PATH
    out = output_path or _OUT_PATH
    if not src.exists():
        return []
    all_q = [json.loads(l) for l in src.read_text(encoding="utf-8").splitlines() if l.strip()]
    by_seed: dict[str, list[dict]] = defaultdict(list)
    for q in all_q:
        by_seed[q.get("seed_id","unknown")].append(q)

    selected: list[dict] = []
    for seed_id, qs in by_seed.items():
        qs_sorted = sorted(qs, key=lambda q: (
            _PRIORITY_TYPES.index(q.get("query_type","")) if q.get("query_type","") in _PRIORITY_TYPES else 99
        ))
        taken = 0
        for q in qs_sorted:
            if taken >= max_per_seed or len(selected) >= max_queries:
                break
            selected.append({**q, "_selected_for": "mvp_d4"})
            taken += 1

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for q in selected:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")

    # Build report
    rp = report_path or Path("outputs/mvp_d4/selected_queries_report.md")
    from collections import Counter
    type_counts = Counter(q.get("query_type","?") for q in selected)
    seed_counts = Counter(q.get("seed_id","?") for q in selected)
    lines = ["# MVP-D4 Selected Queries Report\n",
             f"- total_available_v2_queries: {len(all_q)}",
             f"- selected_queries: {len(selected)}",
             "\n## By Query Type"] + [f"- {k}: {v}" for k,v in type_counts.most_common()] + \
            ["\n## By Seed"] + [f"- {k}: {v}" for k,v in seed_counts.most_common()] + \
            ["\n## Top 5 Query Examples"] + [f"- [{q.get('query_type','')}] {q.get('query','')}" for q in selected[:5]]
    rp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return selected
