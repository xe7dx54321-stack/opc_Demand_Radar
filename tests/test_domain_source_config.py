"""Tests for domain source config loader."""
from __future__ import annotations
import pytest
from pathlib import Path
from demand_radar.acquisition.domain_source_config import (
    load_domain_config,
    get_search_queries,
    get_domain_title_zh,
    get_source_registry_path,
)


def test_load_domain_config_ai_investment():
    cfg = load_domain_config("ai_investment_tracking")
    assert cfg["domain_id"] == "ai_investment_tracking"
    assert "search_queries" in cfg
    assert len(cfg["search_queries"]) > 0


def test_load_domain_config_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_domain_config("nonexistent_domain", config_dir=tmp_path)


def test_get_search_queries():
    cfg = load_domain_config("ai_investment_tracking")
    queries = get_search_queries(cfg)
    assert isinstance(queries, list)
    assert len(queries) >= 3


def test_get_domain_title_zh():
    cfg = load_domain_config("ai_investment_tracking")
    title = get_domain_title_zh(cfg)
    assert title  # non-empty


def test_source_registry_path():
    path = get_source_registry_path("ai_investment_tracking")
    assert path.exists()
    assert "ai_investment_tracking" in str(path)
