"""YAML configuration loading for Stage 1."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML mapping in {path}")
    return data


def load_configs(config_dir: str | Path = "configs") -> dict[str, dict[str, Any]]:
    config_dir = Path(config_dir)
    return {
        "domain": load_yaml(config_dir / "domain_config.yaml"),
        "sources": load_yaml(config_dir / "source_registry.yaml"),
        "extraction": load_yaml(config_dir / "extraction_config.yaml"),
        "calibration": load_yaml(config_dir / "calibration_config.yaml"),
        "clustering": load_yaml(config_dir / "clustering_config.yaml"),
        "merge_suggestion": load_yaml(config_dir / "merge_suggestion_config.yaml"),
        "batch": load_yaml(config_dir / "batch_config.yaml"),
    }
