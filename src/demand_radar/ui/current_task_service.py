"""Current task service for the D4 second-round review workbench."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

D4_PAIN_PATH = Path("data/processed/mvp_d4/foundation_search_pain_items.jsonl")
D4_SUMMARY_PATH = Path("outputs/mvp_d4/mvp_d4_summary_report.md")


def load_d4_pain_signals(path: Path | str | None = None) -> list[dict[str, Any]]:
    """Load D4 pain signals that are ready for human review."""
    pain_path = Path(path) if path is not None else D4_PAIN_PATH
    if not pain_path.exists() or pain_path.stat().st_size == 0:
        return []

    items: list[dict[str, Any]] = []
    for line in pain_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict) and item.get("should_extract") is True:
            items.append(item)
    return items


def get_current_task_summary(path: Path | str | None = None) -> dict[str, Any]:
    """Return the headline state for the Current Task page."""
    signals = load_d4_pain_signals(path)
    strong = [item for item in signals if item.get("evidence_strength") == "strong"]
    medium = [item for item in signals if item.get("evidence_strength") == "medium"]
    weak = [item for item in signals if item.get("evidence_strength") == "weak"]
    return {
        "data_available": bool(signals),
        "total": len(signals),
        "strong": len(strong),
        "medium": len(medium),
        "weak": len(weak),
        "source": "MVP-D4 Foundation Search Pilot",
        "phase": "第二轮人工审核",
        "can_enter_second_review": len(signals) >= 3,
        "can_enter_product_discovery": False,
        "priority_count": len(strong),
        "pain_items_path": str(Path(path) if path is not None else D4_PAIN_PATH),
    }


def get_d4_summary_report_text(path: Path | str | None = None) -> str | None:
    report_path = Path(path) if path is not None else D4_SUMMARY_PATH
    if report_path.exists():
        return report_path.read_text(encoding="utf-8")
    return None
