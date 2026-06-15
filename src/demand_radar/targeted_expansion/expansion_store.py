"""Store for targeted expansion summary (Stage 3.3)."""
from __future__ import annotations
import json
from pathlib import Path
from demand_radar.targeted_expansion.targeted_schema import TargetedExpansionSummary,TruthScoreDelta
SUMMARY_PATH=Path('data/processed/targeted_expansion_run_summary.json')
DELTA_PATH=Path('data/processed/truth_score_deltas.jsonl')
def write_expansion_summary(s:TargetedExpansionSummary,path=None):
    p=Path(path) if path else SUMMARY_PATH
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(s.model_dump_json(indent=2),encoding='utf-8')
def load_expansion_summary(path=None):
    p=Path(path) if path else SUMMARY_PATH
    if not p.exists(): return None
    try: return TargetedExpansionSummary.model_validate_json(p.read_text(encoding='utf-8'))
    except: return None
def write_truth_score_deltas(deltas:list,path=None):
    p=Path(path) if path else DELTA_PATH
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(chr(10).join(d.model_dump_json() for d in deltas)+chr(10),encoding='utf-8')
def load_truth_score_deltas(path=None):
    p=Path(path) if path else DELTA_PATH
    if not p.exists(): return []
    result=[]
    for line in p.read_text(encoding='utf-8').splitlines():
        if line.strip():
            try: result.append(TruthScoreDelta.model_validate_json(line))
            except: pass
    return result
