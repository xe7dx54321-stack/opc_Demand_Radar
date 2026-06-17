"""MVP-D4: Map Foundation SearchResult to Radar intermediate dicts."""
from __future__ import annotations
import json
from pathlib import Path

_BLOCK_DOMAINS = {"example.com", "example.org", "example.net"}


def _is_blocked(url: str) -> bool:
    ul = (url or "").lower()
    return any(b in ul for b in _BLOCK_DOMAINS)


def map_results(
    foundation_results: list,
    query_meta: dict | None = None,
    output_path: Path | None = None,
) -> list[dict]:
    """Convert Foundation SearchResult objects to Radar-compatible dicts."""
    seen_urls: set[str] = set()
    mapped: list[dict] = []
    qm = query_meta or {}
    for r in foundation_results:
        url = (getattr(r, "url", None) or "").strip()
        if not url or _is_blocked(url) or url in seen_urls:
            continue
        seen_urls.add(url)
        mapped.append({
            "result_id": getattr(r, "result_id", ""),
            "provider": getattr(r, "provider", ""),
            "query_id": qm.get("query_id", ""),
            "seed_id": qm.get("seed_id", ""),
            "pain_item_id": qm.get("pain_item_id"),
            "query": getattr(r, "query", qm.get("query", "")),
            "query_type": qm.get("query_type", ""),
            "title": getattr(r, "title", None),
            "url": url,
            "snippet": getattr(r, "snippet", None),
            "published_at": getattr(r, "published_at", None),
            "rank": getattr(r, "rank", 0),
            "result_domain": getattr(r, "result_domain", ""),
        })
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("a", encoding="utf-8") as f:
            for m in mapped:
                f.write(json.dumps(m, ensure_ascii=False) + "\n")
    return mapped
