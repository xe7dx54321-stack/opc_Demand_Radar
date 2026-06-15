"""Store layer for Evidence Gap Analysis."""
from __future__ import annotations
import json
from pathlib import Path
from demand_radar.evidence_gap.evidence_gap_schema import (
    EvidenceGapAnalysis, TargetedSignalCollectionPlan,
)

GAP_PATH = Path("data/processed/evidence_gap_analysis.jsonl")
PLAN_PATH = Path("data/processed/targeted_signal_collection_plan.jsonl")


def write_gap_analysis(gaps: list[EvidenceGapAnalysis], path: str | Path = GAP_PATH) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [g.model_dump_json() for g in gaps]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return len(gaps)


def load_gap_analysis(path: str | Path = GAP_PATH) -> list[EvidenceGapAnalysis]:
    path = Path(path)
    if not path.exists():
        return []
    result = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            result.append(EvidenceGapAnalysis.model_validate_json(line))
        except Exception:
            continue
    return result


def write_collection_plans(plans: list[TargetedSignalCollectionPlan], path: str | Path = PLAN_PATH) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [p.model_dump_json() for p in plans]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return len(plans)


def load_collection_plans(path: str | Path = PLAN_PATH) -> list[TargetedSignalCollectionPlan]:
    path = Path(path)
    if not path.exists():
        return []
    result = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            result.append(TargetedSignalCollectionPlan.model_validate_json(line))
        except Exception:
            continue
    return result
