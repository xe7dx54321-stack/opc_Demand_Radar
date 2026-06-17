"""MVP-D3: Select queries from calibrated_query_plan_v2."""
from __future__ import annotations
import json
from collections import defaultdict
from pathlib import Path
from demand_radar.mvp_d3.search_provider_schema import SearchQuerySelection
from demand_radar.state.raw_store import utc_now_iso

_V2_PATH = Path("data/processed/mvp_d2/calibrated_query_plan_v2.jsonl")
_SEL_PATH = Path("data/processed/mvp_d3/selected_search_queries.jsonl")
_PRIORITY_TYPES = ["manual_workflow","pain_phrase","spreadsheet_workaround",
                   "workaround_phrase","complaint_phrase","buying_intent"]


def select_queries(v2_path: Path | None = None, output_path: Path | None = None,
                   max_queries: int = 24, max_per_seed: int = 6) -> list[SearchQuerySelection]:
    src = v2_path or _V2_PATH
    out = output_path or _SEL_PATH
    if not src.exists():
        return []
    all_q = [json.loads(l) for l in src.read_text(encoding="utf-8").splitlines() if l.strip()]
    by_seed: dict[str, list[dict]] = defaultdict(list)
    for q in all_q:
        by_seed[q.get("seed_id","unknown")].append(q)
    selected: list[SearchQuerySelection] = []
    for seed_id, qs in by_seed.items():
        qs_sorted = sorted(qs, key=lambda q: _PRIORITY_TYPES.index(q.get("query_type",""))
                           if q.get("query_type","") in _PRIORITY_TYPES else 99)
        taken = 0
        for q in qs_sorted:
            if taken >= max_per_seed or len(selected) >= max_queries:
                break
            selected.append(SearchQuerySelection(
                query_id=q.get("query_id", f"q_{len(selected)}"),
                seed_id=seed_id,
                pain_item_id=q.get("pain_item_id"),
                query=q.get("query",""),
                query_type=q.get("query_type",""),
                connector=q.get("connector","search"),
                priority=q.get("priority","medium"),
                selected_reason_zh=f"query_type={q.get('query_type','')}",
                metadata=q.get("metadata",{}),
            ))
            taken += 1
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for s in selected:
            f.write(s.model_dump_json() + "\n")
    return selected
