"""Stage 3.4: Lineage report generation."""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from demand_radar.lineage.lineage_schema import (
    CandidateLineage, TargetedEvidenceAttribution, StableTruthScoreDelta
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def build_candidate_lineage_report(
    lineages: list[CandidateLineage],
    output_path: str | Path = "outputs/candidate_lineage_report.md",
    lineage_baseline_quality: str = "full",
) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    strength_counts = Counter(l.match_strength for l in lineages)
    before_count = sum(1 for l in lineages if l.before_group_id)
    after_count = sum(1 for l in lineages if l.after_group_id)

    lines = [
        "# Candidate Lineage Report",
        "",
        "## Summary",
        "",
        f"- lineage_baseline_quality: {lineage_baseline_quality}",
        f"- Before candidates: {before_count}",
        f"- After candidates: {after_count}",
        f"- Candidate lineages: {len(lineages)}",
        f"- Strong matches: {strength_counts.get('strong', 0)}",
        f"- Weak matches: {strength_counts.get('weak', 0)}",
        f"- Split candidates: {strength_counts.get('split', 0)}",
        f"- Merged candidates: {strength_counts.get('merged', 0)}",
        f"- Unmatched before: {strength_counts.get('unmatched', 0)}",
        f"- Missing baseline (new after): {strength_counts.get('missing_baseline', 0)}",
        f"- Generated at: {_now()}",
        "",
        "## Lineage Details",
        "",
    ]

    for i, lin in enumerate(lineages, 1):
        lines += [
            f"### {i}. {lin.before_group_title_zh or lin.after_group_title_zh or lin.lineage_id}",
            "",
        ]
        if lin.before_group_id:
            lines += [
                "**Before:**",
                f"- Group ID: `{lin.before_group_id}`",
                f"- Title: {lin.before_group_title_zh or 'N/A'}",
                f"- Score: {lin.before_truth_score or 'N/A'} [{lin.before_truth_level or 'N/A'}]",
                f"- Next Action: {lin.before_next_action or 'N/A'}",
                "",
            ]
        if lin.after_group_id:
            lines += [
                "**After:**",
                f"- Group ID: `{lin.after_group_id}`",
                f"- Title: {lin.after_group_title_zh or 'N/A'}",
                f"- Score: {lin.after_truth_score or 'N/A'} [{lin.after_truth_level or 'N/A'}]",
                f"- Next Action: {lin.after_next_action or 'N/A'}",
                "",
            ]
        lines += [
            "**Match:**",
            f"- Match Score: {lin.match_score:.3f}",
            f"- Match Strength: {lin.match_strength}",
        ]
        if lin.match_reasons:
            lines.append("- Match Reasons: " + "; ".join(lin.match_reasons))
        if lin.drift_flags:
            lines.append("- Drift Flags: " + ", ".join(lin.drift_flags))
        if lin.targeted_signal_ids:
            lines.append(
                f"- Targeted Signals: {len(lin.targeted_signal_ids)} total, "
                f"{len(lin.matched_targeted_signal_ids)} matched, "
                f"{len(lin.unmatched_targeted_signal_ids)} unmatched"
            )
        lines += ["", f"**Lineage Summary:** {lin.lineage_summary_zh}", "", "---", ""]

    output_path.write_text("\n".join(lines), encoding="utf-8")


def build_targeted_evidence_attribution_report(
    attributions: list[TargetedEvidenceAttribution],
    output_path: str | Path = "outputs/targeted_evidence_attribution_report.md",
) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    status_counts = Counter(a.attribution_status for a in attributions)
    total = len(attributions)
    attributed = (
        status_counts.get("attributed_to_expected_group", 0)
        + status_counts.get("attributed_to_related_group", 0)
    )
    attribution_rate = attributed / total if total else 0.0

    lines = [
        "# Targeted Evidence Attribution Report",
        "",
        "## Summary",
        "",
        f"- Targeted signals: {total}",
        f"- Attributed to expected group: {status_counts.get('attributed_to_expected_group', 0)}",
        f"- Attributed to related group: {status_counts.get('attributed_to_related_group', 0)}",
        f"- Lost in extraction: {status_counts.get('lost_in_extraction', 0)}",
        f"- Lost in clustering: {status_counts.get('lost_in_clustering', 0)}",
        f"- Lost in merge: {status_counts.get('lost_in_merge', 0)}",
        f"- Not used / excluded: {status_counts.get('not_used', 0) + status_counts.get('excluded_or_invalid', 0)}",
        f"- Attribution rate: {attribution_rate:.1%}",
        f"- Generated at: {_now()}",
        "",
    ]

    # Group by target_group_id
    by_group: dict[str, list[TargetedEvidenceAttribution]] = {}
    for a in attributions:
        gid = a.target_group_id or "unknown"
        by_group.setdefault(gid, []).append(a)

    lines += ["## By Target Candidate", ""]
    for i, (gid, items) in enumerate(by_group.items(), 1):
        title = items[0].target_group_title_zh or gid
        g_counts = Counter(a.attribution_status for a in items)
        g_attributed = (
            g_counts.get("attributed_to_expected_group", 0)
            + g_counts.get("attributed_to_related_group", 0)
        )
        g_rate = g_attributed / len(items) if items else 0.0
        intent_counts = Counter(a.evidence_intent for a in items if a.evidence_intent)

        lines += [
            f"### {i}. {title}",
            "",
            f"- Target Group: `{gid}`",
            f"- Targeted Signals: {len(items)}",
            f"- Attributed (expected): {g_counts.get('attributed_to_expected_group', 0)}",
            f"- Attributed (related): {g_counts.get('attributed_to_related_group', 0)}",
            f"- Lost in extraction: {g_counts.get('lost_in_extraction', 0)}",
            f"- Lost in clustering: {g_counts.get('lost_in_clustering', 0)}",
            f"- Lost in merge: {g_counts.get('lost_in_merge', 0)}",
            f"- Attribution rate: {g_rate:.1%}",
            "",
            "Evidence Intents:",
        ]
        for intent, cnt in sorted(intent_counts.items()):
            lines.append(f"- {intent}: {cnt}")
        lines += ["", "---", ""]

    output_path.write_text("\n".join(lines), encoding="utf-8")


def build_stable_truth_score_delta_report(
    stable_deltas: list[StableTruthScoreDelta],
    output_path: str | Path = "outputs/stable_truth_score_delta_report.md",
) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    conf_counts = Counter(d.delta_confidence for d in stable_deltas)
    improved = [d for d in stable_deltas if d.stable_delta and d.stable_delta > 0]
    declined = [d for d in stable_deltas if d.stable_delta and d.stable_delta < 0]
    new_proceed = [
        d for d in stable_deltas
        if d.recommended_next_action == "proceed_to_fit_scoring"
    ]

    lines = [
        "# Stable Truth Score Delta Report",
        "",
        "## Summary",
        "",
        f"- Compared lineages: {len(stable_deltas)}",
        f"- High confidence deltas: {conf_counts.get('high', 0)}",
        f"- Medium confidence deltas: {conf_counts.get('medium', 0)}",
        f"- Low confidence deltas: {conf_counts.get('low', 0)}",
        f"- Improved: {len(improved)}",
        f"- Declined: {len(declined)}",
        f"- New proceed_to_fit_scoring: {len(new_proceed)}",
        f"- Generated at: {_now()}",
        "",
        "## Stable Deltas",
        "",
    ]

    for i, d in enumerate(
        sorted(stable_deltas, key=lambda x: -(x.stable_delta or 0)), 1
    ):
        delta_str = (
            f"+{d.stable_delta:.1f}" if d.stable_delta and d.stable_delta > 0
            else (f"{d.stable_delta:.1f}" if d.stable_delta is not None else "N/A")
        )
        lines += [
            f"### {i}. {d.before_group_title_zh or d.after_group_title_zh or d.stable_delta_id}",
            "",
            f"Before Score: {d.before_truth_score or 'N/A'} [{d.before_truth_level or 'N/A'}]",
            f"After Score: {d.after_truth_score or 'N/A'} [{d.after_truth_level or 'N/A'}]",
            f"Stable Delta: {delta_str}",
            f"Delta Confidence: **{d.delta_confidence}**",
        ]
        if d.drift_flags:
            lines.append(f"Drift Flags: {', '.join(d.drift_flags)}")
        if d.improvement_dimensions:
            lines.append(f"Improvement Dimensions: {', '.join(d.improvement_dimensions)}")
        if d.remaining_gaps:
            lines.append(f"Remaining Gaps: {', '.join(d.remaining_gaps)}")
        lines += [
            "",
            f"Interpretation: {d.interpretation_zh}",
            "",
            f"Recommended Next Action: **{d.recommended_next_action}**",
            "",
            "---",
            "",
        ]

    if not stable_deltas:
        lines += ["No lineage data available.", ""]

    output_path.write_text("\n".join(lines), encoding="utf-8")
