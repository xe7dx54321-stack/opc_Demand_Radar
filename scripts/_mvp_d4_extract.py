"""Incremental LLM extraction for MVP-D4 with progress saving."""
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
print(f"LLM: {client.provider} / {client.model}", flush=True)

cand_dicts = [json.loads(l) for l in Path("data/processed/mvp_d4/foundation_search_evidence_candidates.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
gate_items = [json.loads(l) for l in Path("data/processed/mvp_d4/foundation_search_gate_results.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
allowed_ids = {g["candidate_id"] for g in gate_items if g.get("allow")}
allowed_dicts = [c for c in cand_dicts if c["candidate_id"] in allowed_ids]
print(f"Candidates: {len(cand_dicts)}, allowed: {len(allowed_dicts)}", flush=True)

rel_results = [{"candidate_id": c["candidate_id"], "relevance_decision": "include", "relevance_score": 0.65} for c in allowed_dicts]
rel_map = {r["candidate_id"]: r for r in rel_results}

BATCH_SIZE = 30
output_path = Path("data/processed/mvp_d4/foundation_search_pain_items.jsonl")
output_path.write_text("", encoding="utf-8")

all_items = []
total = len(allowed_dicts)
for start in range(0, total, BATCH_SIZE):
    batch = allowed_dicts[start:start+BATCH_SIZE]
    batch_rel = [rel_map[c["candidate_id"]] for c in batch if c["candidate_id"] in rel_map]
    end = min(start+BATCH_SIZE, total)
    print(f"Batch {start//BATCH_SIZE+1}: items {start+1}-{end}", flush=True)
    items = run_pain_extraction(
        batch, batch_rel, llm_client=client, output_path=None,
        run_scope_override="demand_radar_mvp_d4_foundation_search_pilot", max_items=BATCH_SIZE,
    )
    all_items.extend(items)
    with output_path.open("a", encoding="utf-8") as f:
        for item in items:
            f.write(item.model_dump_json() + "\n")
    extracted_batch = sum(1 for i in items if i.should_extract)
    print(f"  Done: {len(items)} processed, {extracted_batch} extracted", flush=True)

extracted_all = [p for p in all_items if p.should_extract]
print(f"\nFINAL: total={len(all_items)}, extracted={len(extracted_all)}")
strengths = {}
for p in extracted_all:
    s = p.evidence_strength or "?"
    strengths[s] = strengths.get(s, 0) + 1
print(f"Strengths: {strengths}")
for p in extracted_all[:10]:
    print(f"  EXTRACTED: {str(p.title or '?')[:70]} | {p.evidence_strength} | conf={p.confidence}")