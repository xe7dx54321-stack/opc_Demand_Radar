"""MVP-B: Reports builder."""
from __future__ import annotations
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe(text: str | None, n: int = 200) -> str:
    if not text:
        return ""
    t = re.sub(r"<[^>]+>", " ", text)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:n]


def build_domain_relevance_report(
    relevance_dicts: list[dict],
    output_path: Path | None = None,
) -> Path:
    out = output_path or Path("outputs/mvp_b/domain_relevance_report.md")
    out.parent.mkdir(parents=True, exist_ok=True)

    total = len(relevance_dicts)
    inc = [r for r in relevance_dicts if r.get("relevance_decision") == "include"]
    unc = [r for r in relevance_dicts if r.get("relevance_decision") == "uncertain"]
    exc = [r for r in relevance_dicts if r.get("relevance_decision") == "exclude"]
    avg_score = sum(r.get("relevance_score", 0) for r in relevance_dicts) / total if total else 0

    lines = [
        "# Domain Relevance Report",
        "",
        f"## Summary",
        "",
        f"- Total candidates: {total}",
        f"- Include: {len(inc)}",
        f"- Uncertain: {len(unc)}",
        f"- Exclude: {len(exc)}",
        f"- Avg relevance score: {avg_score:.3f}",
        f"- Generated at: {_now()}",
        "",
        "## Top Included (by relevance score)",
        "",
    ]
    for r in sorted(inc, key=lambda x: x.get("relevance_score", 0), reverse=True)[:10]:
        lines += [
            f"- [{r.get('relevance_score', 0):.2f}] {r.get('source_url','')[:80]}",
            f"  reason: {(r.get('domain_reason_zh') or '')[:100]}",
        ]

    lines += ["", "## Top Excluded", ""]
    for r in sorted(exc, key=lambda x: x.get("relevance_score", 0))[:10]:
        lines += [
            f"- [{r.get('relevance_score', 0):.2f}] {r.get('source_url','')[:80]}",
            f"  reason: {(r.get('exclude_reason_zh') or '')[:100]}",
        ]

    lines += ["", "## Uncertain", ""]
    for r in unc[:5]:
        lines.append(f"- [{r.get('relevance_score', 0):.2f}] {r.get('source_url','')[:80]}")

    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def build_pain_extraction_report(
    pain_dicts: list[dict],
    output_path: Path | None = None,
) -> Path:
    out = output_path or Path("outputs/mvp_b/pain_extraction_report.md")
    out.parent.mkdir(parents=True, exist_ok=True)

    total = len(pain_dicts)
    extracted = [p for p in pain_dicts if p.get("should_extract")]
    rejected = [p for p in pain_dicts if not p.get("should_extract")]

    strength_cnt = Counter(p.get("evidence_strength", "reject") for p in pain_dicts)
    stype_cnt = Counter(p.get("source_type", "") for p in extracted)
    pain_type_cnt = Counter(p.get("pain_type") for p in extracted if p.get("pain_type"))
    workflow_cnt = Counter(p.get("workflow_stage") for p in extracted if p.get("workflow_stage"))
    commercial_n = sum(
        1 for p in extracted
        if p.get("commercial_signal_type") not in ("no_commercial_signal", "unclear", None)
    )

    lines = [
        "# Pain Extraction Report",
        "",
        "## Summary",
        "",
        f"- Items processed: {total}",
        f"- Should extract (true): {len(extracted)}",
        f"- Rejected: {len(rejected)}",
        f"- Strong: {strength_cnt.get('strong', 0)}",
        f"- Medium: {strength_cnt.get('medium', 0)}",
        f"- Weak: {strength_cnt.get('weak', 0)}",
        f"- Reject: {strength_cnt.get('reject', 0)}",
        f"- Commercial signal: {commercial_n}",
        f"- Generated at: {_now()}",
        "",
        "## By Source Type",
        "",
    ]
    for stype, cnt in stype_cnt.most_common():
        lines.append(f"- {stype}: {cnt}")

    lines += ["", "## By Pain Type", ""]
    for ptype, cnt in pain_type_cnt.most_common():
        lines.append(f"- {ptype}: {cnt}")

    lines += ["", "## By Workflow Stage", ""]
    for wf, cnt in workflow_cnt.most_common():
        lines.append(f"- {wf}: {cnt}")

    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def build_top_pain_signals_report(
    pain_dicts: list[dict],
    n: int = 20,
    output_path: Path | None = None,
) -> Path:
    out = output_path or Path("outputs/mvp_b/top_pain_signals_report.md")
    out.parent.mkdir(parents=True, exist_ok=True)

    extracted = [
        p for p in pain_dicts
        if p.get("should_extract") and p.get("evidence_strength") in ("strong", "medium", "weak")
    ]
    top = sorted(
        extracted,
        key=lambda p: (
            {"strong": 3, "medium": 2, "weak": 1}.get(p.get("evidence_strength", ""), 0),
            p.get("confidence", 0),
        ),
        reverse=True,
    )[:n]

    lines = [
        f"# Top {n} Pain Signals Report",
        "",
        f"- Total extracted: {len(extracted)}",
        f"- Generated at: {_now()}",
        "",
    ]

    for i, p in enumerate(top, 1):
        lines += [
            f"## {i}. {(p.get('title') or p.get('candidate_id',''))[:80]}",
            "",
            f"- source_url: {p.get('source_url','')[:120]}",
            f"- persona: {p.get('persona') or 'N/A'}",
            f"- workflow_stage: {p.get('workflow_stage') or 'N/A'}",
            f"- pain_type: {p.get('pain_type') or 'N/A'}",
            f"- evidence_strength: {p.get('evidence_strength')} | confidence: {p.get('confidence', 0):.2f}",
            f"- commercial_signal: {p.get('commercial_signal_type') or 'N/A'}",
            "",
            f"**Pain (ZH):** {p.get('pain_description_zh') or 'N/A'}",
            "",
            f"**Evidence quote:** {_safe(p.get('evidence_quote'), 300)}",
            "",
            f"**Current solution:** {p.get('current_solution') or 'N/A'}",
            "",
        ]

    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def build_mvp_b_summary_report(
    relevance_dicts: list[dict],
    pain_dicts: list[dict],
    r1_before: dict,
    r1_after: dict,
    output_path: Path | None = None,
) -> Path:
    out = output_path or Path("outputs/mvp_b/mvp_b_summary_report.md")
    out.parent.mkdir(parents=True, exist_ok=True)

    total_rel = len(relevance_dicts)
    inc = sum(1 for r in relevance_dicts if r.get("relevance_decision") == "include")
    exc = sum(1 for r in relevance_dicts if r.get("relevance_decision") == "exclude")

    total_pain = len(pain_dicts)
    extracted_n = sum(1 for p in pain_dicts if p.get("should_extract"))
    strong_n = sum(1 for p in pain_dicts if p.get("evidence_strength") == "strong")
    medium_n = sum(1 for p in pain_dicts if p.get("evidence_strength") == "medium")

    eng_pass = (extracted_n >= 10 and (strong_n + medium_n) >= 5)
    prod_pass = (strong_n >= 3 and extracted_n >= 10 and inc >= 10)

    lines = [
        "# MVP-B Summary Report",
        "",
        f"- Generated at: {_now()}",
        "",
        "## Domain Relevance",
        "",
        f"- Total candidates: {total_rel}",
        f"- Include: {inc} | Exclude: {exc}",
        "",
        "## Pain Extraction",
        "",
        f"- Processed: {total_pain}",
        f"- Should extract: {extracted_n}",
        f"- Strong: {strong_n} | Medium: {medium_n}",
        "",
        "## R1 Validation Comparison",
        "",
        f"- Before (draft): valid={r1_before.get('valid',0)} warning={r1_before.get('warning',0)} invalid={r1_before.get('invalid',0)}",
        f"- After (filled): valid={r1_after.get('valid',0)} warning={r1_after.get('warning',0)} invalid={r1_after.get('invalid',0)}",
        "",
        "## Product Acceptance",
        "",
        f"- **engineering_acceptance**: {'PASS' if eng_pass else 'PARTIAL'}",
        f"- **product_acceptance**: {'PASS' if prod_pass else 'PARTIAL'}",
        "",
        "### Criteria",
        f"- extracted >= 10: {extracted_n >= 10}",
        f"- strong + medium >= 5: {strong_n + medium_n >= 5}",
        f"- strong >= 3: {strong_n >= 3}",
        f"- include >= 10: {inc >= 10}",
        "",
        "## Recommendation",
        "",
    ]
    if prod_pass:
        lines.append("> **Can proceed to MVP-C** (human review workbench for extracted pain signals).")
    elif eng_pass:
        lines.append("> **Engineering pass, product partial.** Consider second-pass prompt calibration or more targeted queries before MVP-C.")
    else:
        lines.append("> **MVP-B partial.** Needs more domain-relevant signals or LLM prompt calibration.")

    out.write_text("\n".join(lines), encoding="utf-8")
    return out

def build_llm_pass_report(
    rel_dicts: list[dict],
    pain_dicts: list[dict],
    provider: str = "anthropic_compatible",
    model: str = "claude-sonnet-4-6",
    real_llm_run: bool = True,
    prompt_version: str = "acquired_signal_pain_extraction_v1",
    radar_commit: str = "unknown",
    foundation_commit: str = "b6d23bc",
    output_path: "Path | None" = None,
) -> "Path":
    from pathlib import Path as _Path
    out = output_path or _Path("outputs/mvp_b/mvp_b_llm_pass_report.md")
    out.parent.mkdir(parents=True, exist_ok=True)

    selected = [r for r in rel_dicts if r.get("relevance_decision") in ("include", "uncertain")]
    processed = [p for p in pain_dicts if p.get("candidate_id") in {r.get("candidate_id") for r in selected}]

    should_extract_items = [p for p in processed if p.get("should_extract")]
    rejected = [p for p in processed if not p.get("should_extract")]
    strong = [p for p in processed if p.get("evidence_strength") == "strong"]
    medium = [p for p in processed if p.get("evidence_strength") == "medium"]
    weak = [p for p in processed if p.get("evidence_strength") == "weak"]
    reject = [p for p in processed if p.get("evidence_strength") == "reject"]
    failures = [p for p in processed if "failed after retry" in (p.get("reject_reason") or "")]
    cache_hits = sum(1 for p in processed if p.get("metadata", {}).get("cache_hit"))

    quote_present = sum(1 for p in processed if p.get("evidence_quote"))
    quote_matched = sum(1 for p in processed if p.get("metadata", {}).get("quote_matched"))
    persona_pop = sum(1 for p in processed if p.get("persona"))
    workflow_pop = sum(1 for p in processed if p.get("workflow_stage"))
    pain_type_pop = sum(1 for p in processed if p.get("pain_type"))
    commercial_ct = sum(1 for p in processed if p.get("commercial_signal_type") not in (None, "no_commercial_signal", "unclear"))

    lines = [
        "# MVP-B LLM Pass Report",
        "",
        "## Run Metadata",
        "",
        f"- generated_at: {_now()}",
        f"- radar_commit: {radar_commit}",
        f"- foundation_commit: {foundation_commit}",
        f"- provider: {provider}",
        f"- model: {model}",
        f"- real_llm_run: {real_llm_run}",
        f"- prompt_version: {prompt_version}",
        f"- cache_enabled: true",
        "",
        "## Input Summary",
        "",
        f"- total_candidates: {len(rel_dicts)}",
        f"- include: {sum(1 for r in rel_dicts if r.get('relevance_decision') == 'include')}",
        f"- uncertain: {sum(1 for r in rel_dicts if r.get('relevance_decision') == 'uncertain')}",
        f"- selected_for_llm: {len(selected)}",
        "",
        "## LLM Extraction Summary",
        "",
        f"- processed: {len(processed)}",
        f"- should_extract_true: {len(should_extract_items)}",
        f"- rejected: {len(rejected)}",
        f"- strong: {len(strong)}",
        f"- medium: {len(medium)}",
        f"- weak: {len(weak)}",
        f"- reject_strength: {len(reject)}",
        f"- failures: {len(failures)}",
        f"- cache_hits: {cache_hits}",
        "",
        "## Quality Checks",
        "",
        f"- evidence_quote_present: {quote_present}/{len(processed)}",
        f"- evidence_quote_matched_raw_text: {quote_matched}/{quote_present if quote_present else 1}",
        f"- persona_populated: {persona_pop}/{len(processed)}",
        f"- workflow_stage_populated: {workflow_pop}/{len(processed)}",
        f"- pain_type_populated: {pain_type_pop}/{len(processed)}",
        f"- commercial_signal_count: {commercial_ct}",
        "",
        "## Top Extracted Pain Items",
        "",
    ]

    top = sorted(
        should_extract_items,
        key=lambda x: (
            {"strong": 3, "medium": 2, "weak": 1}.get(x.get("evidence_strength", ""), 0),
            x.get("confidence", 0),
        ),
        reverse=True,
    )

    if not top:
        lines.append("_No pain items extracted. Check domain relevance or LLM configuration._")
    else:
        for item in top:
            title = _safe(item.get("title") or item.get("candidate_id", ""), 80)
            lines += [
                f"### {title}",
                "",
                f"- source_url: {item.get('source_url', '')}",
                f"- persona: {item.get('persona', '-')}",
                f"- workflow_stage: {item.get('workflow_stage', '-')}",
                f"- pain_type: {item.get('pain_type', '-')}",
                f"- evidence_strength: {item.get('evidence_strength', '-')} | confidence: {item.get('confidence', 0):.2f}",
                f"- commercial_signal: {item.get('commercial_signal_type', '-')}",
                "",
                f"**Pain (ZH):** {_safe(item.get('pain_description_zh'), 200)}",
                "",
                f"**Evidence quote:** {_safe(item.get('evidence_quote'), 300)}",
                "",
                f"**Current solution:** {_safe(item.get('current_solution')) or 'N/A'}",
                "",
            ]

    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def build_r1_validation_comparison_report(
    r1_before: dict,
    r1_after: dict,
    before_path: str = "examples/real_evidence_pack_ai_investment_tracking_draft.csv",
    after_path: str = "examples/real_evidence_pack_ai_investment_tracking_filled.csv",
    output_path: "Path | None" = None,
) -> "Path":
    from pathlib import Path as _Path
    out = output_path or _Path("outputs/mvp_b/r1_validation_after_extraction_report.md")
    out.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# R1 Validation: Before vs After LLM Extraction",
        "",
        f"- generated_at: {_now()}",
        "",
        "## Before (Draft CSV)",
        "",
        f"- input: {before_path}",
        f"- valid: {r1_before.get('valid', 0)}",
        f"- warning: {r1_before.get('warning', 0)}",
        f"- invalid: {r1_before.get('invalid', 0)}",
        "",
        "## After (Filled CSV from LLM Pass)",
        "",
        f"- input: {after_path}",
        f"- valid: {r1_after.get('valid', 0)}",
        f"- warning: {r1_after.get('warning', 0)}",
        f"- invalid: {r1_after.get('invalid', 0)}",
        "",
        "## Delta",
        "",
        f"- valid delta: {r1_after.get('valid', 0) - r1_before.get('valid', 0):+d}",
        f"- warning delta: {r1_after.get('warning', 0) - r1_before.get('warning', 0):+d}",
        f"- invalid delta: {r1_after.get('invalid', 0) - r1_before.get('invalid', 0):+d}",
        "",
    ]

    out.write_text("\n".join(lines), encoding="utf-8")
    return out
