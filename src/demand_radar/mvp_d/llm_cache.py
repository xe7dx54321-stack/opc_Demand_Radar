"""Provenance-aware cache for MVP-D pain extraction LLM calls."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_CACHE_PATH = Path(".llm_cache/mvp_d/expansion_pain_extraction_cache.jsonl")


def raw_text_hash(raw_text: str) -> str:
    """Return a stable hash for the exact raw text sent to the LLM."""
    return hashlib.sha256((raw_text or "").encode("utf-8")).hexdigest()


def cache_key(
    *,
    candidate_id: str,
    provider: str,
    model: str,
    prompt_version: str,
    run_scope: str,
    raw_hash: str,
) -> str:
    payload = {
        "candidate_id": candidate_id,
        "provider": provider,
        "model": model,
        "prompt_version": prompt_version,
        "run_scope": run_scope,
        "raw_text_hash": raw_hash,
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


@dataclass
class MVPDPainExtractionCacheStats:
    reads: int = 0
    writes: int = 0
    stale_prevented: int = 0
    disabled: int = 0


class MVPDPainExtractionCache:
    """JSONL cache that only reuses exact provenance matches."""

    def __init__(
        self,
        path: str | Path = DEFAULT_CACHE_PATH,
        enabled: bool = True,
    ) -> None:
        self.path = Path(path)
        self.enabled = enabled
        self.stats = MVPDPainExtractionCacheStats()
        self._store: dict[str, dict[str, Any]] = {}
        self._candidate_keys: dict[str, set[str]] = {}
        if self.enabled and self.path.exists():
            self._load()

    def _load(self) -> None:
        for line in self.path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            key = str(entry.get("key") or "")
            candidate_id = str(entry.get("candidate_id") or "")
            if not key or not candidate_id:
                continue
            self._store[key] = entry
            self._candidate_keys.setdefault(candidate_id, set()).add(key)

    def get(
        self,
        *,
        candidate_id: str,
        provider: str,
        model: str,
        prompt_version: str,
        run_scope: str,
        raw_hash: str,
    ) -> dict[str, Any] | None:
        if not self.enabled:
            self.stats.disabled += 1
            return None
        key = cache_key(
            candidate_id=candidate_id,
            provider=provider,
            model=model,
            prompt_version=prompt_version,
            run_scope=run_scope,
            raw_hash=raw_hash,
        )
        entry = self._store.get(key)
        if entry is None:
            if self._candidate_keys.get(candidate_id):
                self.stats.stale_prevented += 1
            return None
        self.stats.reads += 1
        result = entry.get("result")
        return result if isinstance(result, dict) else None

    def set(
        self,
        *,
        candidate_id: str,
        provider: str,
        model: str,
        prompt_version: str,
        run_scope: str,
        raw_hash: str,
        result: dict[str, Any],
    ) -> None:
        if not self.enabled:
            return
        key = cache_key(
            candidate_id=candidate_id,
            provider=provider,
            model=model,
            prompt_version=prompt_version,
            run_scope=run_scope,
            raw_hash=raw_hash,
        )
        entry = {
            "key": key,
            "candidate_id": candidate_id,
            "provider": provider,
            "model": model,
            "prompt_version": prompt_version,
            "run_scope": run_scope,
            "raw_text_hash": raw_hash,
            "result": result,
        }
        self._store[key] = entry
        self._candidate_keys.setdefault(candidate_id, set()).add(key)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self.stats.writes += 1
