"""Stage R1: UI service for real evidence summary."""
from __future__ import annotations
import json
from pathlib import Path

_ITEMS_PATH = Path("data/processed/real_evidence_items.jsonl")
_VALIDATION_PATH = Path("data/processed/real_evidence_validation.jsonl")
_REVIEWS_PATH = Path("data/processed/real_evidence_calibration_reviews.jsonl")


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


def get_real_evidence_summary() -> dict:
    items = _load_jsonl(_ITEMS_PATH)
    validations = _load_jsonl(_VALIDATION_PATH)
    reviews = _load_jsonl(_REVIEWS_PATH)

    valid_n = sum(1 for v in validations if v.get("status") == "valid")
    warn_n = sum(1 for v in validations if v.get("status") == "warning")
    inv_n = sum(1 for v in validations if v.get("status") == "invalid")
    excl_n = sum(1 for v in validations if v.get("status") == "excluded")

    url_n = sum(1 for i in items if i.get("source_url"))
    url_ratio = url_n / len(items) if items else 0.0

    user_voice = sum(
        1 for i in items
        if i.get("source_type") in (
            "product_review", "community_discussion", "github_issue", "interview_note", "forum_post"
        )
    )

    paid_signal = sum(
        1 for i in items
        if i.get("paid_alternative") or i.get("budget_signal")
        or "paid" in (i.get("commercial_signal_type") or "")
        or "budget" in (i.get("commercial_signal_type") or "")
    )

    workaround = sum(
        1 for i in items
        if i.get("current_solution") or "workaround" in (i.get("evidence_type") or "")
    )

    return {
        "evidence_items": len(items),
        "valid": valid_n,
        "warning": warn_n,
        "invalid": inv_n,
        "excluded": excl_n,
        "source_url_ratio": url_ratio,
        "user_voice_signals": user_voice,
        "paid_or_cost_signals": paid_signal,
        "workaround_signals": workaround,
        "calibration_reviews": len(reviews),
    }


def get_real_evidence_items() -> list[dict]:
    return _load_jsonl(_ITEMS_PATH)


def get_real_evidence_validations() -> list[dict]:
    return _load_jsonl(_VALIDATION_PATH)


def get_calibration_reviews() -> list[dict]:
    return _load_jsonl(_REVIEWS_PATH)