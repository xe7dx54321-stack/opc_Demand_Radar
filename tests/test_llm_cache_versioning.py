"""Tests for LLM semantic merge cache versioning (Stage 2.9D).

Verifies that cache keys include prompt_version, provider, gate_policy_version,
and that no_read / force_rerun / clear() modes work correctly.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from demand_radar.semantic_merge.llm_cache import LLMSemanticMergeCache, _cache_key


# ---------------------------------------------------------------------------
# Cache key isolation tests
# ---------------------------------------------------------------------------

def test_different_prompt_version_misses_cache():
    """Different prompt_version must NOT share cache entries."""
    key_v1 = _cache_key("mc1", "ca1", "cb1", "model-x", prompt_version="v1")
    key_v2 = _cache_key("mc1", "ca1", "cb1", "model-x", prompt_version="semantic_merge_judge_v2")
    assert key_v1 != key_v2


def test_different_model_misses_cache():
    """Different model must NOT share cache entries."""
    key_a = _cache_key("mc1", "ca1", "cb1", "gpt-4o", prompt_version="v2")
    key_b = _cache_key("mc1", "ca1", "cb1", "claude-3", prompt_version="v2")
    assert key_a != key_b


def test_different_provider_misses_cache():
    """Different provider must NOT share cache entries."""
    key_openai = _cache_key("mc1", "ca1", "cb1", "m", provider="openai_compatible")
    key_anthropic = _cache_key("mc1", "ca1", "cb1", "m", provider="anthropic_compatible")
    assert key_openai != key_anthropic


def test_different_gate_policy_version_misses_cache():
    """Different gate_policy_version must NOT share cache entries."""
    key_v1 = _cache_key("mc1", "ca1", "cb1", "m", gate_policy_version="v1")
    key_v2 = _cache_key("mc1", "ca1", "cb1", "m", gate_policy_version="semantic_merge_gate_v2")
    assert key_v1 != key_v2


def test_same_params_same_key():
    """Same params produce the same key (deterministic)."""
    k1 = _cache_key("mc1", "ca1", "cb1", "model", prompt_version="v2", provider="fake", gate_policy_version="v2")
    k2 = _cache_key("mc1", "ca1", "cb1", "model", prompt_version="v2", provider="fake", gate_policy_version="v2")
    assert k1 == k2


# ---------------------------------------------------------------------------
# Cache behaviour tests
# ---------------------------------------------------------------------------

_FAKE_RESULT = {"decision": "confirm_merge", "confidence": 0.9, "reason_zh": "test"}


def _make_cache(path: Path, **kwargs) -> LLMSemanticMergeCache:
    return LLMSemanticMergeCache(
        path=path,
        prompt_version=kwargs.get("prompt_version", "v2"),
        provider=kwargs.get("provider", "fake"),
        gate_policy_version=kwargs.get("gate_policy_version", "v2"),
        enabled=kwargs.get("enabled", True),
        no_read=kwargs.get("no_read", False),
        force_rerun=kwargs.get("force_rerun", False),
    )


def test_normal_cache_read_write(tmp_path):
    """Written entry can be read back in the same session."""
    cache = _make_cache(tmp_path / "cache.jsonl")
    cache.set("mc1", "ca1", "cb1", "model-x", _FAKE_RESULT)
    result = cache.get("mc1", "ca1", "cb1", "model-x")
    assert result == _FAKE_RESULT
    assert cache.stats.writes == 1
    assert cache.stats.reads == 1


def test_cache_miss_cross_session(tmp_path):
    """Entry written with v2 prompt must not be read by v1 prompt cache."""
    cache_v2 = _make_cache(tmp_path / "cache.jsonl", prompt_version="semantic_merge_judge_v2")
    cache_v2.set("mc1", "ca1", "cb1", "model", _FAKE_RESULT)

    # Load with v1 prompt - must miss
    cache_v1 = _make_cache(tmp_path / "cache.jsonl", prompt_version="v1")
    result = cache_v1.get("mc1", "ca1", "cb1", "model")
    assert result is None
    assert cache_v1.stats.reads == 0


def test_no_read_mode_skips_reading(tmp_path):
    """no_read=True should not return cached results."""
    cache_write = _make_cache(tmp_path / "cache.jsonl")
    cache_write.set("mc1", "ca1", "cb1", "model", _FAKE_RESULT)

    cache_no_read = _make_cache(tmp_path / "cache.jsonl", no_read=True)
    result = cache_no_read.get("mc1", "ca1", "cb1", "model")
    assert result is None
    assert cache_no_read.stats.bypassed >= 1


def test_no_read_still_writes(tmp_path):
    """no_read cache should still write new results."""
    cache = _make_cache(tmp_path / "cache.jsonl", no_read=True)
    cache.set("mc1", "ca1", "cb1", "model", _FAKE_RESULT)
    assert cache.stats.writes == 1
    # Verify file was written
    assert (tmp_path / "cache.jsonl").exists()


def test_force_rerun_skips_reading(tmp_path):
    """force_rerun should not return cached results."""
    cache_write = _make_cache(tmp_path / "cache.jsonl")
    cache_write.set("mc1", "ca1", "cb1", "model", _FAKE_RESULT)

    cache_force = _make_cache(tmp_path / "cache.jsonl", force_rerun=True)
    result = cache_force.get("mc1", "ca1", "cb1", "model")
    assert result is None
    assert cache_force.stats.bypassed >= 1


def test_force_rerun_overwrites_existing(tmp_path):
    """force_rerun should overwrite existing cache entry."""
    cache = _make_cache(tmp_path / "cache.jsonl")
    cache.set("mc1", "ca1", "cb1", "model", _FAKE_RESULT)

    new_result = {"decision": "reject_merge", "confidence": 0.8, "reason_zh": "updated"}
    cache_force = _make_cache(tmp_path / "cache.jsonl", force_rerun=True)
    cache_force.set("mc1", "ca1", "cb1", "model", new_result)

    # Load fresh cache and verify updated result
    cache_fresh = _make_cache(tmp_path / "cache.jsonl")
    result = cache_fresh.get("mc1", "ca1", "cb1", "model")
    assert result is not None
    assert result["decision"] == "reject_merge"


def test_clear_removes_all_entries(tmp_path):
    """clear() should delete all cache entries."""
    cache = _make_cache(tmp_path / "cache.jsonl")
    cache.set("mc1", "ca1", "cb1", "model", _FAKE_RESULT)
    cache.set("mc2", "ca2", "cb2", "model", _FAKE_RESULT)
    assert cache.size == 2

    removed = cache.clear()
    assert removed == 2
    assert cache.size == 0
    assert not (tmp_path / "cache.jsonl").exists()


def test_clear_fresh_cache_returns_zero(tmp_path):
    """clear() on empty cache returns 0."""
    cache = _make_cache(tmp_path / "cache.jsonl")
    removed = cache.clear()
    assert removed == 0


def test_stats_reads_incremented_on_hit(tmp_path):
    cache = _make_cache(tmp_path / "cache.jsonl")
    cache.set("mc1", "ca1", "cb1", "model", _FAKE_RESULT)
    cache.get("mc1", "ca1", "cb1", "model")
    cache.get("mc1", "ca1", "cb1", "model")
    assert cache.stats.reads == 2
    assert cache.stats.writes == 1


def test_stale_prevented_counted_on_no_read(tmp_path):
    """When no_read=True and existing key exists, stale_prevented should increment."""
    # First, write an entry normally
    cache_write = _make_cache(tmp_path / "cache.jsonl")
    cache_write.set("mc1", "ca1", "cb1", "model", _FAKE_RESULT)

    # Now open with no_read; stale_prevented should count known-stale skips
    cache_no_read = _make_cache(tmp_path / "cache.jsonl", no_read=True)
    cache_no_read.get("mc1", "ca1", "cb1", "model")
    # stale_prevented is incremented when key is found in store but skipped
    assert cache_no_read.stats.stale_prevented >= 1
    assert cache_no_read.stats.bypassed >= 1


def test_entry_includes_versioning_fields(tmp_path):
    """Cache file entries must include prompt_version, provider, gate_policy_version."""
    cache = _make_cache(
        tmp_path / "cache.jsonl",
        prompt_version="semantic_merge_judge_v2",
        provider="anthropic_compatible",
        gate_policy_version="semantic_merge_gate_v2",
    )
    cache.set("mc1", "ca1", "cb1", "model", _FAKE_RESULT)

    entries = [json.loads(l) for l in (tmp_path / "cache.jsonl").read_text().splitlines() if l.strip()]
    assert len(entries) == 1
    entry = entries[0]
    assert entry["prompt_version"] == "semantic_merge_judge_v2"
    assert entry["provider"] == "anthropic_compatible"
    assert entry["gate_policy_version"] == "semantic_merge_gate_v2"
