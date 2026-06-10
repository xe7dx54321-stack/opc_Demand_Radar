"""Manual CSV/JSONL import for Stage 1 Raw State."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from demand_radar.config.schemas import RawSignal
from demand_radar.state.quarantine_store import append_quarantine
from demand_radar.state.raw_store import (
    append_raw_signals,
    load_raw_signals,
    make_content_hash,
    next_id,
    utc_now_iso,
)


KNOWN_FIELDS = {
    "title",
    "raw_text",
    "url",
    "source_name",
    "source_type",
    "published_at",
    "language",
    "domain_tags",
    "batch_id",
    "source_note",
    "signal_focus",
    "expected_quality",
}


def import_file(
    input_path: str | Path,
    output_path: str | Path = "data/raw/raw_signals.jsonl",
    quarantine_path: str | Path = "data/quarantine/invalid_outputs.jsonl",
) -> list[RawSignal]:
    input_path = Path(input_path)
    rows = _read_rows(input_path)
    existing = load_raw_signals(output_path)
    existing_ids = [signal.raw_signal_id for signal in existing]
    seen_hashes = {signal.content_hash for signal in existing}
    imported: list[RawSignal] = []
    next_signal_id = next_id("sig", existing_ids)

    for row in rows:
        row = _normalize_row(row)
        title = str(row.get("title") or "").strip()
        raw_text = str(row.get("raw_text") or "").strip()
        if not raw_text:
            append_quarantine("raw_signal", "empty_text", row, path=quarantine_path)
            continue
        if not title:
            append_quarantine("raw_signal", "schema_invalid", row, path=quarantine_path)
            continue

        content_hash = make_content_hash(title, raw_text)
        if content_hash in seen_hashes:
            append_quarantine("raw_signal", "duplicate_signal", row, path=quarantine_path)
            continue

        payload = {
            "raw_signal_id": next_signal_id,
            "source_name": str(row.get("source_name") or "manual_import").strip(),
            "source_type": str(row.get("source_type") or "manual").strip(),
            "title": title,
            "raw_text": raw_text,
            "url": _optional_text(row.get("url")),
            "published_at": _optional_text(row.get("published_at")),
            "collected_at": utc_now_iso(),
            "language": _optional_text(row.get("language")),
            "domain_tags": _split_tags(row.get("domain_tags")),
            "batch_id": _optional_text(row.get("batch_id")),
            "source_note": _optional_text(row.get("source_note")),
            "signal_focus": _optional_text(row.get("signal_focus")),
            "expected_quality": _optional_text(row.get("expected_quality")),
            "metadata": _metadata_from_extra_fields(row),
            "content_hash": content_hash,
        }
        try:
            signal = RawSignal.model_validate(payload)
        except ValidationError as exc:
            append_quarantine("raw_signal", "schema_invalid", {"row": row, "errors": exc.errors()}, path=quarantine_path)
            continue

        imported.append(signal)
        seen_hashes.add(content_hash)
        next_signal_id = next_id("sig", existing_ids + [signal.raw_signal_id for signal in imported])

    append_raw_signals(imported, output_path)
    return imported


def _read_rows(input_path: Path) -> list[dict[str, Any]]:
    suffix = input_path.suffix.lower()
    if suffix == ".csv":
        with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    if suffix in {".jsonl", ".ndjson"}:
        rows: list[dict[str, Any]] = []
        with input_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(json.loads(line))
        return rows
    raise ValueError(f"Unsupported import format: {input_path.suffix}")


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in row.items():
        normalized[str(key).strip()] = value.strip() if isinstance(value, str) else value
    return normalized


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _split_tags(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    separator = ";" if ";" in text else ","
    return [part.strip() for part in text.split(separator) if part.strip()]


def _metadata_from_extra_fields(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key not in KNOWN_FIELDS and value not in ("", None)}
