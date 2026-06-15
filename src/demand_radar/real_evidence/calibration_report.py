"""Stage R1: calibration_report - build markdown reports."""
from __future__ import annotations
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from demand_radar.real_evidence.real_evidence_schema import (
    RealEvidenceItem,
    RealEvidenceValidation,
    CalibrationReview,
)

_OUT = Path("outputs")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_real_evidence_pack_report(
    items: list[RealEvidenceItem],
    validations: list[RealEvidenceValidation],
    output_path: Path | None = None,
) -> Path:
    out = output_path or _OUT / "real_evidence_pack_report.md"
    out.parent.mkdir(parents=True, exist_ok=True)

    total = len(validations)
    valid_n = sum(1 for v in validations if v.status == "valid")
    warn_n = sum(1 for v in validations if v.status == "warning")
    inv_n = sum(1 for v in validations if v.status == "invalid")
    excl_n = sum(1 for v in validations if v.status == "excluded")

    source_url_n = sum(1 for i in items if i.source_url)
    url_ratio = f"{source_url_n/len(items):.1%}" if items else "N/A"

    source_type_cnt = Counter(i.source_type for i in items)

    user_voice = sum(
        1 for i in items
        if i.source_type in ("product_review", "community_discussion", "github_issue", "interview_note", "forum_post")
    )
    user_voice_ratio = f"{user_voice/len(items):.1%}" if items else "N/A"

    paid_signal = sum(
        1 for i in items
        if any(x in (i.commercial_signal_type or "") for x in ("paid_tool", "budget", "purchasing_intent", "existing_vendor"))
        or i.paid_alternative
        or i.budget_signal
    )
    paid_ratio = f"{paid_signal/len(items):.1%}" if items else "N/A"

    workaround_signal = sum(
        1 for i in items
        if i.current_solution
        or "workaround" in (i.evidence_type or "")
        or "manual" in (i.pain_type or "")
    )
    workaround_ratio = f"{workaround_signal/len(items):.1%}" if items else "N/A"

    lines = [
        "# Real Evidence Pack Report",
        "",
        "## Summary",
        "",
        f"- Target direction: AI 产业跟踪与项目初筛",
        f"- Evidence items: {len(items)}",
        f"- Total validated: {total}",
        f"- Valid: {valid_n}",
        f"- Warning: {warn_n}",
        f"- Invalid: {inv_n}",
        f"- Excluded: {excl_n}",
        f"- Source URL ratio: {url_ratio}",
        f"- User voice signals: {user_voice} ({user_voice_ratio})",
        f"- Paid / cost signals: {paid_signal} ({paid_ratio})",
        f"- Workaround signals: {workaround_signal} ({workaround_ratio})",
        f"- Generated at: {_now()}",
        "",
        "## Source Type Distribution",
        "",
    ]
    for stype, cnt in source_type_cnt.most_common():
        lines.append(f"- {stype}: {cnt}")

    lines += [
        "",
        "## Evidence Quality",
        "",
    ]
    high_val_types = {"product_review", "community_discussion", "github_issue", "case_study", "pricing_page", "interview_note", "job_posting"}
    high_q = [i for i in items if i.source_type in high_val_types]
    lines.append(f"- High-value source items: {len(high_q)}")
    lines.append(f"- Other source items: {len(items) - len(high_q)}")

    if items:
        lines += ["", "## Evidence Samples", ""]
        for item in items[:5]:
            lines += [
                f"### {item.evidence_id}",
                f"- Source: {item.source_type} | {item.source_url or item.source_note or 'N/A'}",
                f"- Persona: {item.persona or 'N/A'} | Stage: {item.workflow_stage or 'N/A'}",
                f"- Pain type: {item.pain_type or 'N/A'}",
                f"- Quote: {(item.evidence_quote or '')[:120]}",
                "",
            ]

    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def build_calibration_report(
    reviews: list[CalibrationReview],
    output_path: Path | None = None,
) -> Path:
    out = output_path or _OUT / "real_evidence_calibration_report.md"
    out.parent.mkdir(parents=True, exist_ok=True)

    all_labels: list[str] = []
    for r in reviews:
        all_labels.extend(r.human_labels)
    label_cnt = Counter(all_labels)

    lines = [
        "# Real Evidence Calibration Report",
        "",
        "## Summary",
        "",
        f"- Reviewed items: {len(reviews)}",
        f"- True pain: {label_cnt.get('true_pain', 0)}",
        f"- Fake pain: {label_cnt.get('fake_pain', 0)}",
        f"- Too generic: {label_cnt.get('too_generic', 0)}",
        f"- Strong signal: {label_cnt.get('strong_signal', 0)}",
        f"- Weak signal: {label_cnt.get('weak_signal', 0)}",
        f"- Commercial signal: {label_cnt.get('commercial_signal', 0)}",
        f"- Not commercial: {label_cnt.get('not_commercial', 0)}",
        f"- Bad extraction: {label_cnt.get('bad_extraction', 0)}",
        f"- Bad merge: {label_cnt.get('bad_merge', 0)}",
        f"- Missed pain: {label_cnt.get('missed_pain', 0)}",
        f"- Duplicate / noise: {label_cnt.get('duplicate_noise', 0)}",
        f"- Generated at: {_now()}",
        "",
        "## Key Failure Modes",
        "",
    ]
    if label_cnt.get("bad_extraction", 0) > 0:
        lines.append(f"- Extraction errors detected: {label_cnt['bad_extraction']} items need prompt fix.")
    if label_cnt.get("bad_merge", 0) > 0:
        lines.append(f"- Merge errors detected: {label_cnt['bad_merge']} items merged incorrectly.")
    if label_cnt.get("too_generic", 0) > 0:
        lines.append(f"- Too-generic signals: {label_cnt['too_generic']} items should be rejected by rubric.")
    if label_cnt.get("missed_pain", 0) > 0:
        lines.append(f"- Missed pains: {label_cnt['missed_pain']} items suggest extraction prompt gaps.")
    if not reviews:
        lines.append("- No calibration reviews yet. Please use the UI to label evidence items.")

    lines += ["", "## Review Notes", ""]
    for r in reviews[:10]:
        if r.reviewer_note_zh:
            lines.append(f"- [{r.evidence_id}] {r.reviewer_note_zh}")

    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def build_prompt_skill_recommendations(
    reviews: list[CalibrationReview],
    findings: list[dict] | None = None,
    output_path: Path | None = None,
) -> Path:
    out = output_path or _OUT / "prompt_skill_calibration_recommendations.md"
    out.parent.mkdir(parents=True, exist_ok=True)

    findings = findings or []
    all_labels: list[str] = []
    for r in reviews:
        all_labels.extend(r.human_labels)
    label_cnt = Counter(all_labels)

    skill_fixes: list[str] = []
    extract_fixes: list[str] = []
    merge_fixes: list[str] = []
    rubric_fixes: list[str] = []
    rejection_fixes: list[str] = []
    weight_fixes: list[str] = []

    for r in reviews:
        if r.suggested_skill_fix_zh:
            skill_fixes.append(f"- [{r.evidence_id}] {r.suggested_skill_fix_zh}")
        if r.suggested_prompt_fix_zh:
            extract_fixes.append(f"- [{r.evidence_id}] {r.suggested_prompt_fix_zh}")
        if r.suggested_rubric_fix_zh:
            rubric_fixes.append(f"- [{r.evidence_id}] {r.suggested_rubric_fix_zh}")

    for f in findings:
        ft = f.get("finding_type", "")
        desc = f.get("description_zh", "")
        fix = f.get("suggested_fix_zh", "")
        entry = f"- [{ft}] {desc} → {fix}"
        if ft == "extraction_error":
            extract_fixes.append(entry)
        elif ft == "merge_error":
            merge_fixes.append(entry)
        elif ft == "rubric_gap":
            rubric_fixes.append(entry)
        elif ft == "skill_gap":
            skill_fixes.append(entry)
        elif ft == "source_weight_error":
            weight_fixes.append(entry)
        elif ft == "rejection_rule_gap":
            rejection_fixes.append(entry)

    def _section(title: str, items: list[str]) -> list[str]:
        if not items:
            return [f"## {title}", "", "- 暂无发现（需更多人工 review 后补充）", ""]
        return [f"## {title}", ""] + items + [""]

    lines = [
        "# Prompt & Skill Calibration Recommendations",
        "",
        f"Generated at: {_now()}",
        f"Based on: {len(reviews)} calibration reviews, {len(findings)} calibration findings",
        "",
    ]
    lines += _section("Collection Skill Fixes", skill_fixes)
    lines += _section("Pain Extraction Prompt Fixes", extract_fixes)
    lines += _section("Merge Prompt Fixes", merge_fixes)
    lines += _section("Evidence Rubric Fixes", rubric_fixes)
    lines += _section("Rejection Rule Fixes", rejection_fixes)
    lines += _section("Source Weighting Fixes", weight_fixes)

    out.write_text("\n".join(lines), encoding="utf-8")
    return out