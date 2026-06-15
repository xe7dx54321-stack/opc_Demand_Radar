"""Stage 3.5 store layer."""
from __future__ import annotations
import json
from pathlib import Path
from demand_radar.stage35.stage35_schema import (
    Stage35SelectedCandidate, Stage35RunSummary, Stage35GateResult,
)

SELECTED_PATH = Path("data/processed/stage35_selected_candidates.jsonl")
SUMMARY_PATH = Path("data/processed/stage35_run_summary.json")
GATE_PATH = Path("data/processed/stage35_stage4_gate_result.json")


def _write_jsonl(path: Path, items: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(i.model_dump_json() for i in items) + "\n", encoding="utf-8")


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


def write_selected_candidates(items: list[Stage35SelectedCandidate], path=None) -> None:
    _write_jsonl(Path(path) if path else SELECTED_PATH, items)


def load_selected_candidates(path=None) -> list[Stage35SelectedCandidate]:
    return _load_jsonl(Path(path) if path else SELECTED_PATH, Stage35SelectedCandidate)


def write_run_summary(summary: Stage35RunSummary, path=None) -> None:
    p = Path(path) if path else SUMMARY_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(summary.model_dump_json(indent=2), encoding="utf-8")


def load_run_summary(path=None) -> Stage35RunSummary | None:
    p = Path(path) if path else SUMMARY_PATH
    if not p.exists():
        return None
    try:
        return Stage35RunSummary.model_validate_json(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_gate_result(result: Stage35GateResult, path=None) -> None:
    p = Path(path) if path else GATE_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(result.model_dump_json(indent=2), encoding="utf-8")


def load_gate_result(path=None) -> Stage35GateResult | None:
    p = Path(path) if path else GATE_PATH
    if not p.exists():
        return None
    try:
        return Stage35GateResult.model_validate_json(p.read_text(encoding="utf-8"))
    except Exception:
        return None
