"""Raw State JSONL persistence helpers."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from pydantic import BaseModel

from demand_radar.config.schemas import JsonDict, RawSignal


def read_jsonl(path: str | Path) -> list[JsonDict]:
    path = Path(path)
    if not path.exists():
        return []
    rows: list[JsonDict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: str | Path, rows: Iterable[dict[str, Any] | BaseModel], append: bool = False) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    count = 0
    with path.open(mode, encoding="utf-8") as handle:
        for row in rows:
            payload = row.model_dump(mode="json") if isinstance(row, BaseModel) else row
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count


def ensure_jsonl_file(path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("", encoding="utf-8")


def load_raw_signals(path: str | Path = "data/raw/raw_signals.jsonl") -> list[RawSignal]:
    return [RawSignal.model_validate(row) for row in read_jsonl(path)]


def write_raw_signals(signals: Iterable[RawSignal], path: str | Path = "data/raw/raw_signals.jsonl") -> int:
    return write_jsonl(path, signals)


def append_raw_signals(signals: Iterable[RawSignal], path: str | Path = "data/raw/raw_signals.jsonl") -> int:
    return write_jsonl(path, signals, append=True)


def make_content_hash(title: str, raw_text: str) -> str:
    normalized = normalize_for_hash(f"{title}\n{raw_text}")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def normalize_for_hash(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def next_id(prefix: str, existing_ids: Iterable[str]) -> str:
    max_num = 0
    pattern = re.compile(rf"^{re.escape(prefix)}_(\d+)$")
    for existing_id in existing_ids:
        match = pattern.match(existing_id)
        if match:
            max_num = max(max_num, int(match.group(1)))
    return f"{prefix}_{max_num + 1:06d}"


def next_ids(prefix: str, existing_ids: Iterable[str], count: int) -> list[str]:
    first = next_id(prefix, existing_ids)
    start = int(first.rsplit("_", 1)[1])
    return [f"{prefix}_{number:06d}" for number in range(start, start + count)]
