import json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

cands_path = Path("data/processed/acquisition/evidence_candidates.jsonl")
candidates = []
for line in cands_path.read_text(encoding="utf-8").splitlines():
    if line.strip():
        candidates.append(json.loads(line))

valid = [c for c in candidates if c.get("include_in_evidence_pack")]
top10 = sorted(valid, key=lambda c: (len(c.get("detected_signal_types",[])), c.get("source_weight",0)), reverse=True)[:10]

for i, c in enumerate(top10, 1):
    signals = c.get("detected_signal_types", [])
    raw = (c.get("raw_text","") or "")
    # Remove HTML tags for cleaner excerpt
    import re
    raw_clean = re.sub(r"<[^>]+>", " ", raw)
    raw_clean = re.sub(r"\s+", " ", raw_clean).strip()
    excerpt = raw_clean[:300]
    url = c.get("source_url","")
    reasons = []
    if "workflow_signal" in signals: reasons.append("workflow_signal")
    if "paid_signal" in signals: reasons.append("paid_signal")
    if "workaround_signal" in signals: reasons.append("workaround_signal")
    if "time_cost_signal" in signals: reasons.append("time_cost_signal")
    stype = c.get("source_type","")
    if stype in ("community_discussion","github_issue"): reasons.append(f"high-weight({stype})")
    print(f"\n--- Top {i} ---")
    print(f"id: {c['candidate_id']}")
    print(f"title: {(c.get('title') or '(no title)')[:100]}")
    print(f"source_type: {stype}")
    print(f"url: {url[:120]}")
    print(f"status: {c.get('validation_status')} | signals: {signals}")
    print(f"excerpt: {excerpt}")
    print(f"why: {' | '.join(reasons)}")
