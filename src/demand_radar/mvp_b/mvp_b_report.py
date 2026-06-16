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