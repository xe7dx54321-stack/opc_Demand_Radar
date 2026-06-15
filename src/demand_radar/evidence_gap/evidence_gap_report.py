"""Evidence Gap Report builder for Stage 3.2."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from demand_radar.evidence_gap.evidence_gap_schema import EvidenceGapAnalysis, TargetedSignalCollectionPlan


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _pri_emoji(p: str) -> str:
    return {"高": "🔴", "high": "🔴", "medium": "🟡", "low": "🟢"}.get(p, "")


def build_evidence_gap_report(
    gaps: list[EvidenceGapAnalysis],
    output_path: str | Path = "outputs/evidence_gap_report.md",
) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    by_pri = {"high": 0, "medium": 0, "low": 0}
    for g in gaps:
        by_pri[g.priority] = by_pri.get(g.priority, 0) + 1

    lines = [
        "# Evidence Gap Report",
        "",
        "## Summary",
        "",
        f"- Truth candidates analyzed: {len(gaps)}",
        f"- High priority gaps: {by_pri['high']}",
        f"- Medium priority gaps: {by_pri['medium']}",
        f"- Low priority gaps: {by_pri['low']}",
        f"- Generated at: {_now()}",
        "",
        "## Candidate Gap Analysis",
        "",
    ]

    for i, g in enumerate(sorted(gaps, key=lambda x: (x.priority != "high", x.priority != "medium", -x.current_truth_score)), 1):
        pri_label = _pri_emoji(g.priority) + " " + g.priority
        lines += [
            f"### {i}. {g.group_title_zh}",
            "",
            f"Current Truth Score: **{g.current_truth_score:.1f}** / 100",
            f"Current Truth Level: **{g.current_truth_level}**",
            f"Current Next Action: {g.current_next_action}",
            f"Priority: {pri_label}",
            "",
            "**Main Bottleneck Dimensions:**",
        ]
        for b in g.main_bottleneck_dimensions:
            lines.append(f"- {b}: {g.dimension_scores.get(b, 0):.1f}")
        lines += [
            "",
            "**Missing Evidence Types:**",
        ]
        for m in g.missing_evidence_types:
            lines.append(f"- {m}")
        lines += [
            "",
            f"**Gap Reason:** {g.gap_reason_zh}",
            "",
            f"**Upgrade Path:** {g.upgrade_path_zh}",
            "",
            f"**Target New Signals:** {g.target_new_signals}",
            "",
            "---",
            "",
        ]

    output_path.write_text("\n".join(lines), encoding="utf-8")


def build_targeted_signal_plan_report(
    plans: list[TargetedSignalCollectionPlan],
    output_path: str | Path = "outputs/targeted_signal_collection_plan.md",
) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    total_signals = sum(p.target_new_signals for p in plans)
    lines = [
        "# Targeted Signal Collection Plan",
        "",
        "## Summary",
        "",
        f"- Plans: {len(plans)}",
        f"- Total target new signals: {total_signals}",
        f"- Generated at: {_now()}",
        "",
        "## Collection Plans",
        "",
    ]

    for i, p in enumerate(plans, 1):
        lines += [
            f"### {i}. {p.group_title_zh}",
            "",
            f"Target New Signals: {p.target_new_signals}",
        ]
        if p.target_personas:
            lines.append("Target Personas: " + ", ".join(p.target_personas))
        if p.target_source_types:
            lines.append("Target Source Types: " + ", ".join(p.target_source_types))
        if p.target_languages:
            lines.append("Target Languages: " + ", ".join(p.target_languages))
        if p.search_keywords_zh:
            lines += ["", "**Search Keywords ZH:**"]
            for kw in p.search_keywords_zh:
                lines.append(f"- {kw}")
        if p.search_keywords_en:
            lines += ["", "**Search Keywords EN:**"]
            for kw in p.search_keywords_en:
                lines.append(f"- {kw}")
        if p.positive_signal_criteria:
            lines += ["", "**Positive Signal Criteria:**"]
            for c in p.positive_signal_criteria:
                lines.append(f"- {c}")
        if p.negative_signal_criteria:
            lines += ["", "**Negative Signal Criteria:**"]
            for c in p.negative_signal_criteria:
                lines.append(f"- {c}")
        lines += [
            "",
            f"**Collection Notes:** {p.collection_notes_zh}",
            "",
            f"**Expected Impact:** {p.expected_impact_zh}",
            "",
            "---",
            "",
        ]

    output_path.write_text("\n".join(lines), encoding="utf-8")
