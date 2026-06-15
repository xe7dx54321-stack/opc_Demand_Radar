"""Store layer for Stage 3.4 lineage data."""
from __future__ import annotations
from pathlib import Path
from demand_radar.lineage.lineage_schema import (
    CandidateLineage, TargetedEvidenceAttribution, StableTruthScoreDelta
)

LINEAGE_PATH = Path("data/processed/candidate_lineage.jsonl")
ATTRIBUTION_PATH = Path("data/processed/targeted_evidence_attribution.jsonl")
STABLE_DELTA_PATH = Path("data/processed/stable_truth_score_delta.jsonl")


def _write_jsonl(path: Path, items: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = "\n".join(item.model_dump_json() for item in items) + "\n"
    path.write_text(lines, encoding="utf-8")


def _load_jsonl(path: Path, model_class):
    if not path.exists():
        return []
    result = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                result.append(model_class.model_validate_json(line))
            except Exception:
                pass
    return result


def write_candidate_lineage(items: list[CandidateLineage], path=None) -> None:
    _write_jsonl(Path(path) if path else LINEAGE_PATH, items)


def load_candidate_lineage(path=None) -> list[CandidateLineage]:
    return _load_jsonl(Path(path) if path else LINEAGE_PATH, CandidateLineage)


def write_targeted_evidence_attribution(items: list[TargetedEvidenceAttribution], path=None) -> None:
    _write_jsonl(Path(path) if path else ATTRIBUTION_PATH, items)


def load_targeted_evidence_attribution(path=None) -> list[TargetedEvidenceAttribution]:
    return _load_jsonl(Path(path) if path else ATTRIBUTION_PATH, TargetedEvidenceAttribution)


def write_stable_truth_score_delta(items: list[StableTruthScoreDelta], path=None) -> None:
    _write_jsonl(Path(path) if path else STABLE_DELTA_PATH, items)


def load_stable_truth_score_delta(path=None) -> list[StableTruthScoreDelta]:
    return _load_jsonl(Path(path) if path else STABLE_DELTA_PATH, StableTruthScoreDelta)