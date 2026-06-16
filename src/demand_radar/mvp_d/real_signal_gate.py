"""MVP-D: Real signal gate - blocks placeholder/example/synthetic candidates."""
from __future__ import annotations
import json
from pathlib import Path
from pydantic import BaseModel
from typing import Any

_BLOCK_DOMAINS = {"example.com", "example.org", "example.net"}
_BLOCK_TITLE_PHRASES = {
    "example domain", "placeholder", "synthetic", "inherited sample",
    "manual seed", "test sample", "mock signal",
}
_BLOCK_META_FLAGS = {"synthetic", "placeholder", "exclude_from_scoring", "inherited_sample"}
_MIN_RAW_TEXT_CHARS = 120


class GateResult(BaseModel):
    candidate_id: str
    allow: bool
    block_reason: str | None = None
    source_url: str | None = None
    source_type: str | None = None
    seed_id: str | None = None
    query_id: str | None = None


def _url_blocked(url: str | None) -> str | None:
    if not url:
        return "source_url_missing"
    ul = url.lower()
    for bd in _BLOCK_DOMAINS:
        if bd in ul:
            return f"blocked_domain:{bd}"
    return None


def _title_blocked(title: str | None) -> str | None:
    if not title:
        return None
    tl = title.lower()
    for phrase in _BLOCK_TITLE_PHRASES:
        if phrase in tl:
            return f"blocked_title_phrase:{phrase}"
    return None


def _meta_blocked(meta: dict) -> str | None:
    for flag in _BLOCK_META_FLAGS:
        val = meta.get(flag)
        if val is True or val == "true" or val == 1:
            return f"metadata_flag:{flag}"
    return None


def is_real_signal(candidate: dict, min_chars: int = _MIN_RAW_TEXT_CHARS) -> GateResult:
    cid = candidate.get("candidate_id", "unknown")
    url = candidate.get("source_url") or ""
    title = candidate.get("title") or ""
    raw_text = candidate.get("raw_text") or ""
    meta = candidate.get("metadata") or {}
    seed_id = meta.get("seed_id")
    query_id = meta.get("seed_query_id")

    reason = _url_blocked(url)
    if not reason:
        reason = _title_blocked(title)
    if not reason:
        reason = _meta_blocked(meta)
    if not reason and len(raw_text.strip()) < min_chars:
        reason = f"raw_text_too_short:{len(raw_text.strip())}"

    return GateResult(
        candidate_id=cid,
        allow=(reason is None),
        block_reason=reason,
        source_url=url or None,
        source_type=candidate.get("source_type"),
        seed_id=seed_id,
        query_id=query_id,
    )


def run_gate(candidates: list[dict], min_chars: int = _MIN_RAW_TEXT_CHARS) -> tuple[list[GateResult], list[GateResult]]:
    allowed, blocked = [], []
    for c in candidates:
        r = is_real_signal(c, min_chars)
        (allowed if r.allow else blocked).append(r)
    return allowed, blocked


def build_gate_report(
    allowed: list[GateResult],
    blocked: list[GateResult],
    output_path: Path | None = None,
) -> str:
    from collections import Counter
    total = len(allowed) + len(blocked)
    reasons = Counter(r.block_reason for r in blocked if r.block_reason)
    ex_blocked = sum(1 for r in blocked if r.block_reason and "example" in r.block_reason)
    ph_blocked = sum(1 for r in blocked if r.block_reason and "placeholder" in r.block_reason)

    lines = [
        "# MVP-D Real Signal Gate Report\n",
        f"- total_candidates: {total}",
        f"- allowed_count: {len(allowed)}",
        f"- blocked_count: {len(blocked)}",
        f"- example_domain_blocked: {ex_blocked}",
        f"- placeholder_blocked: {ph_blocked}",
        "\n## Block Reason Distribution",
    ]
    for reason, cnt in reasons.most_common():
        lines.append(f"- {reason}: {cnt}")
    lines.append("\n## Allowed Examples (up to 5)")
    for r in allowed[:5]:
        lines.append(f"- {r.candidate_id}: {r.source_url}")
    lines.append("\n## Blocked Examples (up to 5)")
    for r in blocked[:5]:
        lines.append(f"- {r.candidate_id}: {r.block_reason} | {r.source_url}")

    report = "\n".join(lines) + "\n"
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
    return report