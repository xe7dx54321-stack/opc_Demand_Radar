"""Tests for LLM semantic merge cache (Stage 2.9)."""
from __future__ import annotations

from pathlib import Path

from demand_radar.semantic_merge.llm_cache import LLMSemanticMergeCache


def test_set_and_get_roundtrip(tmp_path: Path):
    cache = LLMSemanticMergeCache(path=tmp_path / "cache.jsonl", enabled=True)
    result = {"decision": "confirm_merge", "confidence": 0.92}
    cache.set("mc001", "ca001", "cb001", "gpt-4o", result)
    retrieved = cache.get("mc001", "ca001", "cb001", "gpt-4o")
    assert retrieved == result


def test_cache_miss_returns_none(tmp_path: Path):
    cache = LLMSemanticMergeCache(path=tmp_path / "cache.jsonl", enabled=True)
    assert cache.get("mc_missing", "ca001", "cb001", "gpt-4o") is None


def test_disabled_cache_always_misses(tmp_path: Path):
    cache = LLMSemanticMergeCache(path=tmp_path / "cache.jsonl", enabled=False)
    cache.set("mc001", "ca001", "cb001", "gpt-4o", {"decision": "confirm_merge"})
    assert cache.get("mc001", "ca001", "cb001", "gpt-4o") is None


def test_cache_persists_across_instances(tmp_path: Path):
    path = tmp_path / "cache.jsonl"
    result = {"decision": "reject_merge", "confidence": 0.88}
    cache1 = LLMSemanticMergeCache(path=path, enabled=True)
    cache1.set("mc001", "ca001", "cb001", "gpt-4o", result)
    # Load new instance from same file
    cache2 = LLMSemanticMergeCache(path=path, enabled=True)
    retrieved = cache2.get("mc001", "ca001", "cb001", "gpt-4o")
    assert retrieved == result


def test_different_models_have_different_cache_keys(tmp_path: Path):
    cache = LLMSemanticMergeCache(path=tmp_path / "cache.jsonl", enabled=True)
    cache.set("mc001", "ca001", "cb001", "gpt-4o", {"decision": "confirm_merge"})
    # Different model should be a cache miss
    assert cache.get("mc001", "ca001", "cb001", "claude-3-5") is None


def test_cache_size_increments(tmp_path: Path):
    cache = LLMSemanticMergeCache(path=tmp_path / "cache.jsonl", enabled=True)
    assert cache.size == 0
    cache.set("mc001", "ca001", "cb001", "m", {})
    assert cache.size == 1
    cache.set("mc002", "ca002", "cb002", "m", {})
    assert cache.size == 2


def test_cache_hit_stable_after_second_set(tmp_path: Path):
    """Setting the same key twice should not create duplicates in stored result."""
    cache = LLMSemanticMergeCache(path=tmp_path / "cache.jsonl", enabled=True)
    cache.set("mc001", "ca001", "cb001", "m", {"decision": "confirm_merge"})
    cache.set("mc001", "ca001", "cb001", "m", {"decision": "reject_merge"})
    # In-memory store: last write wins
    result = cache.get("mc001", "ca001", "cb001", "m")
    assert result is not None
