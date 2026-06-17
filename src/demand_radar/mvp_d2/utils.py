"""Shared helpers for MVP-D2 modules."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Iterable

import yaml
from pydantic import BaseModel


def load_yaml_section(path: str | Path, section: str) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    value = data.get(section, {})
    return value if isinstance(value, dict) else {}


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            rows.append(item)
    return rows


def write_jsonl(path: str | Path, rows: Iterable[dict[str, Any] | BaseModel]) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            payload = row.model_dump(mode="json") if isinstance(row, BaseModel) else row
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count


def read_markdown_kv(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        return {}
    data: dict[str, Any] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        text = line.strip()
        if not text.startswith("- ") or ":" not in text:
            continue
        key, value = text[2:].split(":", 1)
        value = value.strip()
        if value.lower() in {"true", "false"}:
            data[key.strip()] = value.lower() == "true"
            continue
        try:
            data[key.strip()] = int(value)
            continue
        except ValueError:
            pass
        try:
            data[key.strip()] = float(value)
            continue
        except ValueError:
            pass
        try:
            data[key.strip()] = json.loads(value)
        except Exception:
            data[key.strip()] = None if value == "n/a" else value
    return data


def load_dotenv(path: str | Path = ".env") -> None:
    path = Path(path)
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def count_by(rows: Iterable[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key) or "unknown")
        counts[value] = counts.get(value, 0) + 1
    return counts


def truncate(text: str | None, max_chars: int = 180) -> str:
    value = " ".join(str(text or "").split())
    return value if len(value) <= max_chars else value[: max_chars - 1] + "…"
