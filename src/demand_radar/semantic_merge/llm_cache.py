"""Cache for LLM semantic merge judgments (Stage 2.9 / 2.9D).

Cache key includes: merge_candidate_id, cluster_id_a, cluster_id_b, model, provider,
prompt_version, gate_policy_version -- so different calibration runs do not share entries.

Modes:
- normal: read from cache if hit; write new results to cache
- no_read: skip reading cache (cache_hit never returns a value); write new results
- force_rerun: skip reading; overwrite existing key in cache file with new results
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_CACHE_PATH = Path("data/cache/llm_semantic_merge_cache.jsonl")

# Sentinel versions
DEFAULT_PROMPT_VERSION = "v1"
DEFAULT_GATE_POLICY_VERSION = "v1"
DEFAULT_PROVIDER = "unknown"


def _cache_key(
    merge_candidate_id: str,
    cluster_id_a: str,
    cluster_id_b: str,
    model: str,
    prompt_version: str = DEFAULT_PROMPT_VERSION,
    provider: str = DEFAULT_PROVIDER,
    gate_policy_version: str = DEFAULT_GATE_POLICY_VERSION,
) -> str:
    """Compute a SHA-256 cache key from all version-relevant fields."""
    payload = json.dumps(
        [
            merge_candidate_id,
            cluster_id_a,
            cluster_id_b,
            model,
            prompt_version,
            provider,
            gate_policy_version,
        ],
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


@dataclass
class CacheStats:
    reads: int = 0
    writes: int = 0
    bypassed: int = 0   # calls where cache was not read (no_read / force_rerun)
    stale_prevented: int = 0  # keys found in store but skipped due to no_read mode


class LLMSemanticMergeCache:
    """JSONL-backed cache for LLM judgment results with versioned keys."""

    def __init__(
        self,
        path: str | Path = DEFAULT_CACHE_PATH,
        enabled: bool = True,
        no_read: bool = False,
        force_rerun: bool = False,
        prompt_version: str = DEFAULT_PROMPT_VERSION,
        provider: str = DEFAULT_PROVIDER,
        gate_policy_version: str = DEFAULT_GATE_POLICY_VERSION,
    ) -> None:
        self.path = Path(path)
        self.enabled = enabled
        self.no_read = no_read or force_rerun   # force_rerun implies no_read
        self.force_rerun = force_rerun
        self.prompt_version = prompt_version
        self.provider = provider
        self.gate_policy_version = gate_policy_version
        self.stats = CacheStats()
        self._store: dict[str, dict[str, Any]] = {}
        if self.enabled and self.path.exists():
            self._load()

    def _load(self) -> None:
        for line in self.path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                key = str(entry.get("key", ""))
                if key:
                    self._store[key] = entry
            except json.JSONDecodeError:
                continue

    def _make_key(
        self,
        merge_candidate_id: str,
        cluster_id_a: str,
        cluster_id_b: str,
        model: str,
    ) -> str:
        return _cache_key(
            merge_candidate_id,
            cluster_id_a,
            cluster_id_b,
            model,
            prompt_version=self.prompt_version,
            provider=self.provider,
            gate_policy_version=self.gate_policy_version,
        )

    def get(
        self,
        merge_candidate_id: str,
        cluster_id_a: str,
        cluster_id_b: str,
        model: str,
    ) -> dict[str, Any] | None:
        if not self.enabled:
            self.stats.bypassed += 1
            return None
        key = self._make_key(merge_candidate_id, cluster_id_a, cluster_id_b, model)
        if self.no_read:
            if key in self._store:
                self.stats.stale_prevented += 1
            self.stats.bypassed += 1
            return None
        entry = self._store.get(key)
        if entry is not None:
            self.stats.reads += 1
            return entry.get("result")
        return None

    def set(
        self,
        merge_candidate_id: str,
        cluster_id_a: str,
        cluster_id_b: str,
        model: str,
        result: dict[str, Any],
    ) -> None:
        if not self.enabled:
            return
        key = self._make_key(merge_candidate_id, cluster_id_a, cluster_id_b, model)
        entry = {
            "key": key,
            "merge_candidate_id": merge_candidate_id,
            "cluster_id_a": cluster_id_a,
            "cluster_id_b": cluster_id_b,
            "model": model,
            "prompt_version": self.prompt_version,
            "provider": self.provider,
            "gate_policy_version": self.gate_policy_version,
            "result": result,
        }
        if self.force_rerun and key in self._store:
            # Update existing entry in-memory; rewrite file at end
            self._store[key] = entry
            self._rewrite()
        else:
            self._store[key] = entry
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self.stats.writes += 1

    def _rewrite(self) -> None:
        """Rewrite the cache file with current in-memory store (deduped)."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as fh:
            for entry in self._store.values():
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def clear(self) -> int:
        """Delete all entries from the cache file. Returns number of entries removed."""
        count = len(self._store)
        self._store.clear()
        if self.path.exists():
            self.path.unlink()
        return count

    @property
    def size(self) -> int:
        return len(self._store)
