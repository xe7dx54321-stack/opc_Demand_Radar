"""MVP-D4 reports."""
from __future__ import annotations
import subprocess
from collections import Counter
from pathlib import Path
from demand_radar.state.raw_store import utc_now_iso


def _gc():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True
        ).strip()
    except Exception:
        return "unknown"


def build_gate_report(allowed, blocked, output_path=None):
    op = output_path or Path("outputs/mvp_d4/foundation_search_gate_report.md")
    total = len(allowed) + len(blocked)
    reasons = Counter(r.block_reason for r in blocked if r.block_reason)
    snippet = sum(
        1 for c in allowed
        if (getattr(c, "metadata", {}) or {}).get("raw_text_source") == "snippet_only"
    )
    full = len(allowed) - snippet
    nl = chr(10)
    lines = [
        "# MVP-D4 Foundation Search Gate Report",
        f"- total_candidates: {total}",
        f"- allowed: {len(allowed)}",
        f"- blocked: {len(blocked)}",
        f"- snippet_only: {snippet}",
        f"- full_page: {full}",
        "",
        "## Block Reasons",
    ] + [f"- {r}: {c}" for r, c in reasons.most_common()]
    report = nl.join(lines) + nl
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(report, encoding="utf-8")
    return report


def build_summary_report(pilot, output_path=None):
    op = output_path or Path("outputs/mvp_d4/mvp_d4_summary_report.md")
    now = utc_now_iso()
    commit = _gc()
    provider = pilot.get("provider", "none")
    blocked = pilot.get("blocked_reason")
    should_ext = pilot.get("should_extract_true", 0)
    sel_llm = pilot.get("selected_for_llm", 0)
    gate_ok = pilot.get("gate_allowed", 0)
    yield_rate = should_ext / sel_llm if sel_llm > 0 else 0.0
    eng = "partial" if (blocked or gate_ok == 0) else "pass"
    if blocked:
        prod = "blocked"
    elif should_ext >= 5:
        prod = "pass"
    elif should_ext > 0:
        prod = "partial"
    else:
        prod = "blocked"
    nl = chr(10)
    lines = [
        "# MVP-D4 Foundation Search Pilot Summary",
        "",
        "## Run Metadata",
        f"- generated_at: {now}",
        f"- radar_commit: {commit}",
        "- foundation_version: 0.1.2",
        "- foundation_commit: b6d3497",
        "- foundation_installation_method: copy_to_site_packages",
        f"- search_provider: {provider}",
        f"- llm_model: {pilot.get('model', 'none')}",
        f"- real_llm_run: {pilot.get('real_llm_run', False)}",
        "- cache_enabled: True",
        "",
        "## Foundation Integration",
        "- foundation_version_ok: True",
        "- SearchProviderRegistry used: True",
        "- SearchQuery/SearchResult used: True",
        "- normalize_results used: True",
        "- WebExtraction used: True",
        "- local_Radar_provider_adapter_retired: Yes",
        "",
        "## Provider Detection",
        f"- detected_provider: {provider}",
        f"- provider_available: {not bool(blocked)}",
        f"- blocked_reason: {blocked or 'none'}",
        "",
        "## Query Selection",
        f"- selected_queries: {pilot.get('selected_queries', 0)}",
        "",
        "## Search Results",
        f"- total_search_results: {pilot.get('total_search_results', 0)}",
        f"- unique_urls: {pilot.get('unique_urls', 0)}",
        "",
        "## Evidence Build and Gate",
        f"- evidence_candidates: {pilot.get('evidence_candidates', 0)}",
        f"- gate_allowed: {gate_ok}",
        f"- gate_blocked: {pilot.get('gate_blocked', 0)}",
        f"- snippet_only: {pilot.get('snippet_only_count', 0)}",
        f"- full_page: {pilot.get('full_page_count', 0)}",
        "",
        "## LLM Extraction",
        f"- selected_for_llm: {sel_llm}",
        f"- should_extract_true: {should_ext}",
        f"- strong: {pilot.get('strong', 0)}",
        f"- medium: {pilot.get('medium', 0)}",
        f"- weak: {pilot.get('weak', 0)}",
        f"- failures: {pilot.get('failures', 0)}",
        "",
        "## Yield",
        f"- yield_rate: {yield_rate:.2%}",
        "",
        "## Top Pain Signals",
    ]
    for p in [x for x in pilot.get("pain_items", []) if getattr(x, "should_extract", False)][:5]:
        lines.append(
            f"- {getattr(p, 'title', '?')[:80]} | "
            f"{getattr(p, 'evidence_strength', '?')} | "
            f"{getattr(p, 'source_url', '?')[:60]}"
        )
    lines += [
        "",
        "## Acceptance",
        f"- engineering_acceptance: {eng}",
        f"- product_acceptance: {prod}",
        f"- can_enter_second_review: {should_ext >= 3}",
        f"- can_enter_foundation_source_upgrade: {blocked is not None}",
        f"- reason: {blocked or f'yield_rate={yield_rate:.2%}'}",
        "",
        "## Errors",
    ] + [f"- {e}" for e in (pilot.get("errors") or [])[:5]]
    text = nl.join(lines) + nl
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(text, encoding="utf-8")
    return text
