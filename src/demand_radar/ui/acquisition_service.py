"""UI service for acquisition data."""
from __future__ import annotations
import json
from pathlib import Path

_CANDIDATES_PATH = Path("data/processed/acquisition/evidence_candidates.jsonl")
_RUN_LOG_PATH = Path("data/processed/acquisition/acquisition_run_log.jsonl")


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


def get_acquisition_summary() -> dict:
    run_log = _load_jsonl(_RUN_LOG_PATH)
    candidates = _load_jsonl(_CANDIDATES_PATH)

    if not run_log:
        return {
            "last_run_id": None,
            "raw_signal_count": 0,
            "unique_signal_count": 0,
            "duplicate_count": 0,
            "evidence_candidate_count": 0,
            "valid_candidate_count": 0,
            "warning_candidate_count": 0,
            "invalid_candidate_count": 0,
            "by_source": {},
            "by_source_type": {},
            "errors": [],
            "warnings": [],
        }

    last = run_log[-1]
    return {
        "last_run_id": last.get("run_id"),
        "raw_signal_count": last.get("raw_signal_count", 0),
        "unique_signal_count": last.get("unique_signal_count", 0),
        "duplicate_count": last.get("duplicate_count", 0),
        "evidence_candidate_count": last.get("evidence_candidate_count", 0),
        "valid_candidate_count": last.get("valid_candidate_count", 0),
        "warning_candidate_count": last.get("warning_candidate_count", 0),
        "invalid_candidate_count": last.get("invalid_candidate_count", 0),
        "by_source": last.get("by_source", {}),
        "by_source_type": last.get("by_source_type", {}),
        "errors": last.get("errors", []),
        "warnings": last.get("warnings", []),
    }


def get_evidence_candidates() -> list[dict]:
    return _load_jsonl(_CANDIDATES_PATH)