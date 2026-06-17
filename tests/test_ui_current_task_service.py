"""Current task service tests for Review Console v1."""
from __future__ import annotations

import json
from pathlib import Path

from demand_radar.ui.current_task_service import get_current_task_summary, load_d4_pain_signals


def _write_d4_items(path: Path) -> None:
    rows = []
    for idx, strength in enumerate(["strong"] * 15 + ["medium"] * 31 + ["weak"]):
        rows.append(
            {
                "pain_item_id": f"pain__{idx:06d}",
                "candidate_id": f"cand_{idx}",
                "should_extract": True,
                "title": f"Pain {idx}",
                "evidence_strength": strength,
                "confidence": 0.9 - idx * 0.001,
                "source_url": "https://example.org/not-used-in-this-test",
            }
        )
    rows.append({"pain_item_id": "pain__reject", "should_extract": False})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )


def test_current_task_identifies_47_d4_should_extract_signals(tmp_path: Path) -> None:
    path = tmp_path / "foundation_search_pain_items.jsonl"
    _write_d4_items(path)

    signals = load_d4_pain_signals(path)
    summary = get_current_task_summary(path)

    assert len(signals) == 47
    assert summary["total"] == 47
    assert summary["strong"] == 15
    assert summary["medium"] == 31
    assert summary["weak"] == 1
    assert summary["phase"] == "第二轮人工审核"


def test_current_task_graceful_when_d4_data_missing(tmp_path: Path) -> None:
    summary = get_current_task_summary(tmp_path / "missing.jsonl")

    assert summary["data_available"] is False
    assert summary["total"] == 0
    assert summary["priority_count"] == 0
