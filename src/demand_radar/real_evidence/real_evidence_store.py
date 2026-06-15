"""Stage R1: Store for real evidence data."""
from __future__ import annotations
import json
from pathlib import Path
from demand_radar.real_evidence.real_evidence_schema import (
    RealEvidenceItem,
    RealEvidenceValidation,
    CalibrationReview,
)

_ITEMS_PATH = Path("data/processed/real_evidence_items.jsonl")
_VALIDATION_PATH = Path("data/processed/real_evidence_validation.jsonl")
_REVIEWS_PATH = Path("data/processed/real_evidence_calibration_reviews.jsonl")
_FINDINGS_PATH = Path("data/processed/real_evidence_prompt_calibration_findings.jsonl")


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    items = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                items.append(json.loads(line))
            except Exception:
                pass
    return items


def _append_jsonl(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _write_jsonl(path: Path, objs: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(o, ensure_ascii=False) for o in objs) + "\n",
        encoding="utf-8",
    )


def load_real_evidence_items(path: Path | None = None) -> list[RealEvidenceItem]:
    p = path or _ITEMS_PATH
    return [RealEvidenceItem(**d) for d in _load_jsonl(p)]


def write_real_evidence_items(items: list[RealEvidenceItem], path: Path | None = None) -> None:
    p = path or _ITEMS_PATH
    _write_jsonl(p, [i.model_dump() for i in items])


def load_real_evidence_validations(path: Path | None = None) -> list[RealEvidenceValidation]:
    p = path or _VALIDATION_PATH
    return [RealEvidenceValidation(**d) for d in _load_jsonl(p)]


def write_real_evidence_validations(
    validations: list[RealEvidenceValidation], path: Path | None = None
) -> None:
    p = path or _VALIDATION_PATH
    _write_jsonl(p, [v.model_dump() for v in validations])


def load_calibration_reviews(path: Path | None = None) -> list[CalibrationReview]:
    p = path or _REVIEWS_PATH
    return [CalibrationReview(**d) for d in _load_jsonl(p)]


def append_calibration_review(review: CalibrationReview, path: Path | None = None) -> None:
    p = path or _REVIEWS_PATH
    _append_jsonl(p, review.model_dump())


def write_calibration_reviews(
    reviews: list[CalibrationReview], path: Path | None = None
) -> None:
    p = path or _REVIEWS_PATH
    _write_jsonl(p, [r.model_dump() for r in reviews])


def load_calibration_findings(path: Path | None = None) -> list[dict]:
    p = path or _FINDINGS_PATH
    return _load_jsonl(p)


def write_calibration_findings(findings: list[dict], path: Path | None = None) -> None:
    p = path or _FINDINGS_PATH
    _write_jsonl(p, findings)