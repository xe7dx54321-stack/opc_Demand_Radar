"""Process remaining candidates not yet in output."""
import os, json
from pathlib import Path

for line in Path(".env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

from demand_radar.mvp_b.pain_extraction_runner import run_pain_extraction
from demand_radar.semantic_merge.llm_client import make_llm_client

client = make_llm_client("anthropic_compatible", {})

cand_dicts = [json.loads(l) for l in Path("data/processed/mvp_d4/foundation_search_evidence_candidates.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
gate_items = [json.loads(l) for l in Path("data/processed/mvp_d4/foundation_search_gate_results.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
allowed_ids = {g["candidate_id"] for g in gate_items if g.get("allow")}
allowed_dicts = [c for c in cand_dicts if c["candidate_id"] in allowed_ids]

output_path = Path("data/processed/mvp_d4/foundation_search_pain_items.jsonl")
done_cids = set()
if output_path.exists():
    for l in output_path.read_text(encoding="utf-8").splitlines():
        if l.strip():
            done_cids.add(json.loads(l).get("candidate_id",""))

remaining = [c for c in allowed_dicts if c["candidate_id"] not in done_cids]
print(f"Already done: {len(done_cids)}, remaining: {len(remaining)}", flush=True)

if not remaining:
    print("All done!")
else:
    rel_results = [{"candidate_id": c["candidate_id"], "relevance_decision": "include", "relevance_score": 0.65} for c in remaining]
    items = run_pain_extraction(
        remaining, rel_results, llm_client=client, output_path=None,
        run_scope_override="demand_radar_mvp_d4_foundation_search_pilot", max_items=len(remaining),
    )
    with output_path.open("a", encoding="utf-8") as f:
        for item in items:
            f.write(item.model_dump_json() + "\n")
    extracted = sum(1 for i in items if i.should_extract)
    print(f"Processed {len(items)}, extracted {extracted}", flush=True)

# Final summary
all_items = [json.loads(l) for l in output_path.read_text(encoding="utf-8").splitlines() if l.strip()]
extracted_all = [p for p in all_items if p.get("should_extract")]
print(f"\nFINAL TOTAL: {len(all_items)} items, {len(extracted_all)} extracted")
strengths = {}
for p in extracted_all:
    s = p.get("evidence_strength","?")
    strengths[s] = strengths.get(s,0)+1
print(f"By strength: {strengths}")
for p in extracted_all[:10]:
    print(f"  EXTRACTED: {str(p.get('title','?'))[:70]} | {p.get('evidence_strength')} | conf={p.get('confidence')}")