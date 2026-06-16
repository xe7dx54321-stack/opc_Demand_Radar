"""MVP-C: Real pain signal gate - ensures only real MVP-B signals reach the review UI."""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

_BLOCKED_DOMAINS = {"example.com", "example.org", "example.net"}
_BLOCKED_SOURCE_TYPES = {"manual_seed", "placeholder", "inherited_sample", "manual"}
_REQUIRED_STRENGTHS = {"strong", "medium"}

_CANDIDATES_PATH = Path("data/processed/acquisition/evidence_candidates.jsonl")
_RELEVANCE_PATH = Path("data/processed/mvp_b/domain_relevance_scores.jsonl")


@dataclass
class GateResult:
    pain_item_id: str
    candidate_id: str
    source_url: str | None
    allow: bool
    block_reason: str | None = None

    @property
    def blocked(self) -> bool:
        return not self.allow


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


def _url_domain(url: str) -> str:
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc.lower().lstrip("www.")
    except Exception:
        return url.lower()


def is_real_reviewable_pain_signal(
    item: dict,
    candidate: dict | None = None,
    relevance: dict | None = None,
) -> GateResult:
    """Gate a single extracted pain item. Returns GateResult(allow=True/False)."""
    pid = item.get("pain_item_id", "?")
    cid = item.get("candidate_id", "?")
    url = item.get("source_url") or ""

    # Rule 1: must have should_extract=true
    if not item.get("should_extract"):
        return GateResult(pid, cid, url or None, allow=False,
                          block_reason="should_extract=false")

    # Rule 2: evidence_strength must be strong or medium
    strength = item.get("evidence_strength", "")
    if strength not in _REQUIRED_STRENGTHS:
        return GateResult(pid, cid, url or None, allow=False,
                          block_reason=f"evidence_strength={strength!r} not in {sorted(_REQUIRED_STRENGTHS)}")

    # Rule 3: source_url must be present
    if not url:
        return GateResult(pid, cid, None, allow=False,
                          block_reason="source_url missing")

    # Rule 4: source_url must not be a blocked domain
    domain = _url_domain(url)
    for blocked in _BLOCKED_DOMAINS:
        if domain == blocked or domain.endswith("." + blocked):
            return GateResult(pid, cid, url, allow=False,
                              block_reason=f"source_url domain is blocked placeholder ({domain})")

    # Rule 5: source_type must not be placeholder/manual seed
    stype = (item.get("source_type") or "").lower().replace(" ", "_").replace("-", "_")
    if stype in _BLOCKED_SOURCE_TYPES:
        return GateResult(pid, cid, url, allow=False,
                          block_reason=f"source_type={stype!r} is blocked (placeholder/manual seed)")

    # Rule 6: metadata must not flag synthetic/placeholder/exclude
    meta = item.get("metadata") or {}
    if meta.get("synthetic") or meta.get("placeholder") or meta.get("exclude_from_scoring"):
        return GateResult(pid, cid, url, allow=False,
                          block_reason="metadata flags synthetic/placeholder/exclude_from_scoring=true")

    # Rule 7: must have core fields
    has_title = bool(item.get("title"))
    has_pain = bool(item.get("pain_description_zh"))
    has_quote = bool(item.get("evidence_quote"))
    if not (has_title or has_pain or has_quote):
        return GateResult(pid, cid, url, allow=False,
                          block_reason="missing all core fields: title, pain_description_zh, evidence_quote")

    # Rule 8: if candidate provided, it must trace back to acquisition (have candidate_id prefix)
    if candidate is not None:
        if not candidate.get("candidate_id"):
            return GateResult(pid, cid, url, allow=False,
                              block_reason="candidate has no candidate_id - cannot trace to acquisition")

    # Rule 9: if relevance provided, must be include or uncertain
    if relevance is not None:
        rel_decision = relevance.get("relevance_decision", "")
        if rel_decision == "exclude":
            return GateResult(pid, cid, url, allow=False,
                              block_reason=f"domain_relevance_decision=exclude")

    return GateResult(pid, cid, url, allow=True, block_reason=None)


def run_gate(
    pain_items: list[dict],
    candidates_path: Path | None = None,
    relevance_path: Path | None = None,
) -> tuple[list[GateResult], list[GateResult]]:
    """Run gate on all items. Returns (allowed, blocked)."""
    # Build lookup maps
    cands_raw = _load_jsonl(candidates_path or _CANDIDATES_PATH)
    candidate_map = {c.get("candidate_id"): c for c in cands_raw}

    rel_raw = _load_jsonl(relevance_path or _RELEVANCE_PATH)
    relevance_map = {r.get("candidate_id"): r for r in rel_raw}

    allowed: list[GateResult] = []
    blocked: list[GateResult] = []

    for item in pain_items:
        cid = item.get("candidate_id")
        candidate = candidate_map.get(cid) if cid else None
        relevance = relevance_map.get(cid) if cid else None
        result = is_real_reviewable_pain_signal(item, candidate, relevance)
        if result.allow:
            allowed.append(result)
        else:
            blocked.append(result)

    return allowed, blocked


def build_gate_report(
    pain_items: list[dict],
    allowed: list[GateResult],
    blocked: list[GateResult],
    output_path: Path | None = None,
) -> Path:
    """Generate the data source gate report."""
    out = output_path or Path("outputs/mvp_c/mvp_c_data_source_gate_report.md")
    out.parent.mkdir(parents=True, exist_ok=True)

    from collections import Counter
    block_reasons = Counter(r.block_reason for r in blocked if r.block_reason)

    lines = [
        "# MVP-C Data Source Gate Report",
        "",
        f"Generated at: {_now()}",
        "",
        "## Summary",
        "",
        f"- total_extracted_pain_items: {len(pain_items)}",
        f"- reviewable_count: {len(allowed)}",
        f"- blocked_count: {len(blocked)}",
        "",
        "## Block Reasons",
        "",
    ]
    if block_reasons:
        for reason, count in block_reasons.most_common():
            lines.append(f"- {reason}: {count}")
    else:
        lines.append("- (none)")
    lines.append("")

    lines += ["## Reviewable Signals", ""]
    if allowed:
        for r in allowed:
            item = next((p for p in pain_items if p.get("pain_item_id") == r.pain_item_id), {})
            title = (item.get("title") or r.pain_item_id)[:70]
            lines.append(f"- **{title}**")
            lines.append(f"  - source_url: {r.source_url}")
            lines.append(f"  - candidate_id: {r.candidate_id}")
    else:
        lines.append("_No reviewable signals found._")
    lines.append("")

    lines += ["## Blocked Signals", ""]
    if blocked:
        for r in blocked:
            item = next((p for p in pain_items if p.get("pain_item_id") == r.pain_item_id), {})
            title = (item.get("title") or r.pain_item_id)[:60]
            lines.append(f"- **{title}**")
            lines.append(f"  - source_url: {r.source_url or '(none)'}")
            lines.append(f"  - block_reason: {r.block_reason}")
    else:
        lines.append("_No signals were blocked._")
    lines.append("")

    # Explicit check for Example Domain
    example_blocked = [r for r in blocked if r.source_url and "example.com" in r.source_url.lower()]
    example_passed = [r for r in allowed if r.source_url and "example.com" in r.source_url.lower()]
    lines += [
        "## Example Domain Check",
        "",
        f"- example.com items blocked: {len(example_blocked)}",
        f"- example.com items passed (SHOULD BE 0): {len(example_passed)}",
        f"- Gate status: {'PASS' if len(example_passed) == 0 else 'FAIL - example.com leaked through'}",
        "",
    ]

    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def quarantine_stale_reviews(
    reviews_path: Path,
    allowed_pain_item_ids: set[str],
    quarantine_path: Path | None = None,
) -> tuple[int, int]:
    """Move reviews for blocked items to quarantine. Returns (kept, quarantined)."""
    import json as _json
    qpath = quarantine_path or reviews_path.parent / "quarantined_reviews.jsonl"

    if not reviews_path.exists():
        return 0, 0

    lines = [l for l in reviews_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    keep_lines: list[str] = []
    quar_lines: list[str] = []

    for line in lines:
        try:
            d = _json.loads(line)
            if d.get("pain_item_id") in allowed_pain_item_ids:
                keep_lines.append(line)
            else:
                quar_lines.append(line)
        except Exception:
            keep_lines.append(line)

    reviews_path.write_text("\n".join(keep_lines) + ("\n" if keep_lines else ""), encoding="utf-8")

    if quar_lines:
        qpath.parent.mkdir(parents=True, exist_ok=True)
        existing_q = []
        if qpath.exists():
            existing_q = [l for l in qpath.read_text(encoding="utf-8").splitlines() if l.strip()]
        qpath.write_text("\n".join(existing_q + quar_lines) + "\n", encoding="utf-8")

    return len(keep_lines), len(quar_lines)
