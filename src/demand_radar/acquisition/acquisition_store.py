"""Store/load acquisition data."""
from __future__ import annotations
import json
from pathlib import Path

from .acquisition_schema import EvidenceCandidate, AcquisitionRunSummary

_RAW_SIGNALS_PATH = Path("data/raw/acquisition/raw_signals.jsonl")
_CANDIDATES_PATH = Path("data/processed/acquisition/evidence_candidates.jsonl")
_DRAFT_PATH = Path("data/processed/acquisition/evidence_pack_draft_items.jsonl")
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


def _write_jsonl(path: Path, objs: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(o, ensure_ascii=False) for o in objs) + "\n",
        encoding="utf-8",
    )


def _append_jsonl(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def write_raw_signals(signals: list[dict], path: Path | None = None) -> None:
    _write_jsonl(path or _RAW_SIGNALS_PATH, signals)


def load_raw_signals(path: Path | None = None) -> list[dict]:
    return _load_jsonl(path or _RAW_SIGNALS_PATH)


def write_evidence_candidates(candidates: list[EvidenceCandidate], path: Path | None = None) -> None:
    _write_jsonl(path or _CANDIDATES_PATH, [c.model_dump() for c in candidates])


def load_evidence_candidates(path: Path | None = None) -> list[EvidenceCandidate]:
    return [EvidenceCandidate(**d) for d in _load_jsonl(path or _CANDIDATES_PATH)]


def append_run_log(summary: AcquisitionRunSummary, path: Path | None = None) -> None:
    _append_jsonl(path or _RUN_LOG_PATH, summary.model_dump())


def load_run_log(path: Path | None = None) -> list[dict]:
    return _load_jsonl(path or _RUN_LOG_PATH)
