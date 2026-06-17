"""Small IO helpers for D5."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import yaml
from pydantic import BaseModel


CONFIG_PATH = Path("configs/demand_theme_grouping_config.yaml")


def load_config(config_path: Path | str | None = None) -> dict[str, Any]:
    path = Path(config_path) if config_path else CONFIG_PATH
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    section = data.get("demand_theme_grouping", data)
    return section if isinstance(section, dict) else {}


def read_jsonl(path: Path | str) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def write_jsonl(path: Path | str, rows: Iterable[dict[str, Any] | BaseModel]) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    lines: list[str] = []
    for row in rows:
        payload = row.model_dump(mode="json") if isinstance(row, BaseModel) else row
        lines.append(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        count += 1
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return count


def output_path(cfg: dict[str, Any], key: str, default: str) -> Path:
    return Path(cfg.get("output", {}).get(key, default))


def input_path(cfg: dict[str, Any], key: str, default: str) -> Path:
    return Path(cfg.get("input", {}).get(key, default))

