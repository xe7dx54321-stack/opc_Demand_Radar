"""Item-by-item extraction with immediate file write."""
import os, json, hashlib
from pathlib import Path

for line in Path(".env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

from demand_radar.mvp_b.pain_extraction_runner import _build_extraction_prompt, _parse_extraction_response, _build_pain_item_from_data, _reject_item
from demand_radar.state.raw_store import next_ids
from demand_radar.semantic_merge.llm_client import make_llm_client

client = make_llm_client("anthropic_compatible", {})
print(f"LLM: {client.provider} / {client.model}", flush=True)

run_scope = "demand_radar_mvp_d4_foundation_search_pilot"
prompt_version = "acquired_signal_pain_extraction_v1"
cache_dir = Path(".llm_cache/mvp_b")
cache_dir.mkdir(parents=True, exist_ok=True)

cand_dicts = [json.loads(l) for l in Path("data/processed/mvp_d4/foundation_search_evidence_candidates.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
gate_items = [json.loads(l) for l in Path("data/processed/mvp_d4/foundation_search_gate_results.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
allowed_ids = {g["candidate_id"] for g in gate_items if g.get("allow")}
cands = [c for c in cand_dicts if c["candidate_id"] in allowed_ids]
print(f"Candidates to process: {len(cands)}", flush=True)

# Generate pain IDs
pain_ids = next_ids("pain_", [], len(cands))

output_path = Path("data/processed/mvp_d4/foundation_search_pain_items.jsonl")
# Check already done
done_cids = set()
if output_path.exists() and output_path.stat().st_size > 0:
    for l in output_path.read_text(encoding="utf-8").splitlines():
        if l.strip():
            done_cids.add(json.loads(l).get("candidate_id",""))

remaining = [(i, c) for i, c in enumerate(cands) if c.get("candidate_id") not in done_cids]
print(f"Already done: {len(done_cids)}, remaining: {len(remaining)}", flush=True)

extracted = 0
total_processed = 0
with output_path.open("a", encoding="utf-8") as f_out:
    for enum_i, (orig_i, c) in enumerate(remaining):
        cid = c.get("candidate_id", f"cand_{orig_i}")
        raw_text = c.get("raw_text", "")
        rel = {"candidate_id": cid, "relevance_decision": "include", "relevance_score": 0.65}
        system_p, user_p = _build_extraction_prompt(c, rel, 6000)
        
        # Check cache
        raw_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
        input_hash = hashlib.sha256((run_scope + prompt_version + cid + user_p[:500]).encode()).hexdigest()[:20]
        cache_file = cache_dir / f"pain_{prompt_version}_{input_hash}.json"
        
        data = None
        cache_hit = False
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text(encoding="utf-8"))
                cache_hit = True
            except Exception:
                data = None
        
        if data is None:
            last_error = None
            for attempt in range(2):
                try:
                    raw = client.complete(system_p, user_p)
                    data = _parse_extraction_response(raw)
                    if data:
                        cache_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
                    break
                except Exception as exc:
                    last_error = exc
                    data = None
        
        pain_id = pain_ids[orig_i]
        if data is None:
            item = _reject_item(pain_id, cid, f"LLM failed: {last_error}",
                c.get("source_url"), c.get("source_type"), c.get("title"),
                model=client.model, prompt_version=prompt_version)
        else:
            try:
                item = _build_pain_item_from_data(pain_id, c, data, client.model, prompt_version,
                    cache_hit=cache_hit, raw_text=raw_text)
                item.metadata = {**(item.metadata or {}), "cache_hit": cache_hit, "provider": client.provider,
                    "run_scope": run_scope, "prompt_version": prompt_version}
            except Exception as exc:
                item = _reject_item(pain_id, cid, f"Build error: {exc}",
                    c.get("source_url"), c.get("source_type"), c.get("title"),
                    model=client.model, prompt_version=prompt_version)
        
        f_out.write(item.model_dump_json() + "\n")
        f_out.flush()
        
        if item.should_extract:
            extracted += 1
        total_processed += 1
        
        if total_processed % 10 == 0 or cache_hit:
            status = "HIT" if cache_hit else "MISS"
            print(f"[{total_processed}/{len(remaining)}] {status} {cid} extract={item.should_extract} str={item.evidence_strength}", flush=True)

print(f"\nDone! Processed={total_processed}, extracted={extracted}", flush=True)

# Final stats
all_items = [json.loads(l) for l in output_path.read_text(encoding="utf-8").splitlines() if l.strip()]
print(f"Total in file: {len(all_items)}, extracted: {sum(1 for p in all_items if p.get('should_extract'))}")