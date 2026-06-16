"""Load and validate domain configs."""
from __future__ import annotations
from pathlib import Path
from typing import Any
import yaml


_DOMAIN_CONFIG_DIR = Path("configs/domain_configs")


def load_domain_config(domain_id: str, config_dir: Path | None = None) -> dict[str, Any]:
    """Load a domain config YAML by domain_id."""
    base = config_dir or _DOMAIN_CONFIG_DIR
    path = base / f"{domain_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Domain config not found: {path}")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_search_queries(domain_config: dict[str, Any]) -> list[str]:
    return domain_config.get("search_queries", [])


def get_domain_title_zh(domain_config: dict[str, Any]) -> str:
    return domain_config.get("domain_title_zh", domain_config.get("domain_id", ""))


def get_source_registry_path(domain_id: str) -> Path:
    return Path(f"configs/source_registry_{domain_id}.yaml")
