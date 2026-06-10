"""Quarantine State persistence."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from demand_radar.config.schemas import QuarantineRecord
from demand_radar.state.raw_store import read_jsonl, utc_now_iso, write_jsonl


def append_quarantine(
    item_type: str,
    reason: str,
    raw_payload: dict[str, Any],
    item_id: str | None = None,
    path: str | Path = "data/quarantine/invalid_outputs.jsonl",
) -> QuarantineRecord:
    existing = read_jsonl(path)
    record = QuarantineRecord(
        quarantine_id=f"quarantine_{len(existing) + 1:06d}",
        item_type=item_type,
        item_id=item_id,
        reason=reason,
        raw_payload=raw_payload,
        created_at=utc_now_iso(),
    )
    write_jsonl(path, [record], append=True)
    return record


def load_quarantine(path: str | Path = "data/quarantine/invalid_outputs.jsonl") -> list[QuarantineRecord]:
    return [QuarantineRecord.model_validate(row) for row in read_jsonl(path)]
