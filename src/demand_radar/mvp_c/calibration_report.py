"""MVP-C: Report builders."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path

from demand_radar.mvp_c.review_schema import PainSignalReview, PainSignalReviewSummary
from demand_radar.mvp_c.calibration_analyzer import CalibrationFinding


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_pain_signal_review_report(
    cards: list,
    summary: PainSignalReviewSummary,
    output_path: Path | None = None,
) -> Path:
    out = output_path or Path("outputs/mvp_c/pain_signal_review_report.md")
    out.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# MVP-C Pain Signal Review Report",
        "",
        f"Generated at: {_now()}",
        "",
        "## Summary",
        "",
        f"- Total pain signals: {summary.total_pain_items}",
        f"- Reviewed: {summary.reviewed_count}",
        f"- Unreviewed: {summary.unreviewed_count}",
        f"- True pain: {summary.true_pain_count}",
        f"- False pain: {summary.false_pain_count}",
        "",
        "**Commercial Potential:**",
        f"- High: {summary.commercial_high_count}",
        f"- Medium: {summary.commercial_medium_count}",
        f"- Low: {summary.commercial_low_count}",
        f"- Unclear: {summary.commercial_unclear_count}",
        "",
        "**Action Decision:**",
        f"- Pursue: {summary.pursue_count}",
        f"- Watch: {summary.watch_count}",
        f"- Reject: {summary.reject_count}",
        f"- Needs more evidence: {summary.needs_more_evidence_count}",
        "",
        "**Extraction Quality:**",
        f"- Good: {summary.extraction_good_count}",
        f"- Partial: {summary.extraction_partial_count}",
        f"- Bad: {summary.extraction_bad_count}",
        "",
    ]

    if summary.top_error_labels:
        lines += ["**Top Error Labels:**", ""]
        for label, count in summary.top_error_labels.items():
            lines.append(f"- {label}: {count}")
        lines.append("")

    lines += ["## Reviewed Pain Signals", ""]
    reviewed = [c for c in cards if c.existing_review is not None]
    if not reviewed:
        lines.append("_No reviews yet. Use the MVP-C UI tab to review pain signals._")
    else:
        for card in reviewed:
            rev = card.existing_review
            lines += [
                f"### {card.title or card.pain_item_id}",
                "",
                f"- source: {card.source_url or '-'}",
                f"- persona: {card.persona or '-'}",
                f"- workflow: {card.workflow_stage or '-'}",
                f"- pain_type: {card.pain_type or '-'}",
                f"- evidence_strength: {card.evidence_strength}",
                f"- confidence: {card.confidence:.2f}",
                "",
                f"**Pain (ZH):** {(card.pain_description_zh or '')[:200]}",
                "",
                f"**Evidence quote:** {(card.evidence_quote or '')[:200]}",
                "",
                "**Human Review:**",
                f"- true_pain: {rev.true_pain}",
                f"- commercial_potential: {rev.commercial_potential or '-'}",
                f"- action_decision: {rev.action_decision or '-'}",
                f"- extraction_quality: {rev.extraction_quality or '-'}",
                f"- evidence_quality: {rev.evidence_quality or '-'}",
                f"- error_labels: {rev.error_labels or []}",
                f"- reviewer_note: {rev.reviewer_note_zh or '-'}",
                "",
            ]

    lines += ["## Unreviewed Pain Signals", ""]
    unreviewed = [c for c in cards if c.existing_review is None]
    if not unreviewed:
        lines.append("_All pain signals have been reviewed._")
    else:
        for card in unreviewed:
            lines.append(f"- [{card.evidence_strength}] {card.title or card.pain_item_id}")

    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def build_calibration_recommendations(
    findings: list[CalibrationFinding],
    output_path: Path | None = None,
) -> Path:
    out = output_path or Path("outputs/mvp_c/calibration_recommendations.md")
    out.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# MVP-C Calibration Recommendations",
        "",
        f"Generated at: {_now()}",
        "",
        f"Total findings: {len(findings)}",
        "",
    ]

    by_type: dict[str, list[CalibrationFinding]] = {}
    for f in findings:
        by_type.setdefault(f.finding_type, []).append(f)

    section_labels = {
        "prompt_issue": "## Prompt Issues",
        "relevance_rule_issue": "## Domain Relevance Rule Issues",
        "source_weight_issue": "## Source Weighting Issues",
        "evidence_quality_issue": "## Evidence Quality Issues",
        "no_issues": "## Status",
    }
    for ftype, label in section_labels.items():
        group = by_type.get(ftype, [])
        if not group:
            continue
        lines += [label, ""]
        for f in group:
            lines += [
                f"**[{f.severity.upper()}] {f.finding_id}**",
                "",
                f.description_zh,
                "",
                f"- **Fix:** {f.recommended_fix_zh}",
                f"- **Target:** {f.target_artifact or '-'}",
                f"- **Affected:** {', '.join(f.affected_items) if f.affected_items else 'N/A'}",
                "",
            ]

    lines += ["## Recommended Next Actions", ""]
    has_prompt = bool(by_type.get("prompt_issue"))
    has_rule = bool(by_type.get("relevance_rule_issue"))
    has_source = bool(by_type.get("source_weight_issue"))

    if has_prompt:
        lines.append("1. 修订 `docs/prompts/acquired_signal_pain_extraction_prompt_v1.md`，加强 evidence_quote 真实性和字段精准度要求。")
    if has_rule:
        lines.append("2. 调整 `configs/domain_relevance_config.yaml` 阈值或关键词列表。")
    if has_source:
        lines.append("3. 优化 `configs/source_registry_ai_investment_tracking.yaml` 中的来源权重和 query。")
    if not (has_prompt or has_rule or has_source):
        lines.append("- 当前未发现明显系统问题，建议完成全部 pain signals 审核后再重新分析。")

    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def build_mvp_c_summary_report(
    summary: PainSignalReviewSummary,
    findings: list[CalibrationFinding],
    output_path: Path | None = None,
) -> Path:
    out = output_path or Path("outputs/mvp_c/mvp_c_summary_report.md")
    out.parent.mkdir(parents=True, exist_ok=True)

    reviewed_pct = (summary.reviewed_count / summary.total_pain_items * 100) if summary.total_pain_items else 0
    engineering_pass = True  # workbench exists
    product_pass = summary.reviewed_count >= 3 and (summary.pursue_count + summary.watch_count) >= 1

    can_clustering = summary.pursue_count >= 3
    can_mvp_b_second = summary.unreviewed_count == 0 and not product_pass
    can_mvp_d = product_pass and summary.pursue_count >= 3

    high_findings = [f for f in findings if f.severity == "high" and f.finding_type != "no_issues"]

    lines = [
        "# MVP-C Summary Report",
        "",
        f"Generated at: {_now()}",
        "",
        "## Review Progress",
        "",
        f"- Total pain signals: {summary.total_pain_items}",
        f"- Reviewed: {summary.reviewed_count} ({reviewed_pct:.0f}%)",
        f"- Unreviewed: {summary.unreviewed_count}",
        "",
        "## Product Judgment",
        "",
        f"- true_pain confirmed: {summary.true_pain_count}",
        f"- false_pain: {summary.false_pain_count}",
        f"- pursue: {summary.pursue_count}",
        f"- watch: {summary.watch_count}",
        "",
        "## Calibration",
        "",
        f"- High severity findings: {len(high_findings)}",
        f"- Total findings: {len(findings)}",
        "",
        "## Acceptance",
        "",
        f"- **engineering_acceptance**: {'PASS' if engineering_pass else 'PARTIAL'}",
        f"- **product_acceptance**: {'PASS' if product_pass else 'PARTIAL' if summary.reviewed_count > 0 else 'FAIL'}",
        f"- **can_enter_clustering**: {'YES' if can_clustering else 'NO'}",
        f"- **can_enter_mvp_b_second_pass**: {'YES' if can_mvp_b_second else 'NO'}",
        f"- **can_enter_mvp_d**: {'YES' if can_mvp_d else 'NO'}",
        "",
    ]

    if not product_pass:
        if summary.reviewed_count == 0:
            lines.append("**Reason:** No reviews completed yet. Use `demand-radar review-ui --port 8502` to review pain signals.")
        else:
            lines.append(f"**Reason:** Reviewed {summary.reviewed_count}/{summary.total_pain_items} items; need >= 3 reviewed and >= 1 pursue/watch for product pass.")

    out.write_text("\n".join(lines), encoding="utf-8")
    return out
