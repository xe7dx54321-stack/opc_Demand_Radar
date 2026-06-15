"""Build markdown reports for Stage 3 Truth Scoring."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from demand_radar.truth_scoring.truth_schema import TruthScore


def _now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _level_emoji(level: str) -> str:
    return {"strong": "\U0001f7e2", "medium": "\U0001f7e1", "weak": "\U0001f7e0", "insufficient": "\U0001f534"}.get(level, "")


def _action_label(action: str) -> str:
    labels = {
        "proceed_to_fit_scoring": "\u53ef\u8fdb\u884c Fit Scoring",
        "needs_more_evidence": "\u9700\u8981\u66f4\u591a\u8bc1\u636e",
        "keep_watch": "\u6301\u7eed\u89c2\u5bdf",
        "discard": "\u5efa\u8bae\u4e22\u5f03",
    }
    return labels.get(action, action)


def build_truth_scoring_report(
    scores: list[TruthScore],
    output_path: str | Path = "outputs/truth_scoring_report.md",
) -> None:
    """Write the full Truth Scoring report to markdown."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    level_counts = {"strong": 0, "medium": 0, "weak": 0, "insufficient": 0}
    action_counts: dict[str, int] = {}
    for s in scores:
        level_counts[s.truth_level] = level_counts.get(s.truth_level, 0) + 1
        action_counts[s.recommended_next_action] = action_counts.get(s.recommended_next_action, 0) + 1

    source_label = scores[0].source_type if scores else "n/a"

    # Determine input file path label
    from demand_radar.truth_scoring.truth_input_loader import SOURCE_PATHS, resolve_source_type_label
    raw_src = scores[0].source_type.replace("_ai_reviewed_group","").replace("_reviewed_group","") if scores else "n/a"
    src_key = {v:k for k,v in {k: resolve_source_type_label(k) for k in SOURCE_PATHS}.items()}.get(source_label, raw_src)
    input_file = str(SOURCE_PATHS.get(src_key, "n/a"))

    # Stub warning
    stub_warning = ""
    if len(scores) < 5:
        stub_warning = (
            "\n> \u26a0\ufe0f WARNING: input group count ({}) is below "
            "recommended minimum (5). Results may be based on stub/test data.\n".format(len(scores))
        )

    lines: list[str] = [
        "# Truth Scoring Report",
        "",
        "## Run Summary",
        "",
        f"- Input source: {source_label}",
        f"- Input groups file: {input_file}",
        f"- Reviewed groups: {len(scores)}",
        f"- Truth scores: {len(scores)}",
        f"- Strong: {level_counts['strong']}",
        f"- Medium: {level_counts['medium']}",
        f"- Weak: {level_counts['weak']}",
        f"- Insufficient: {level_counts['insufficient']}",
        f"- Generated at: {_now_str()}",
        "",
    ]
    if stub_warning:
        lines.append(stub_warning)
    lines += [
        "## Score Distribution",
        "",
        "| Level | Count |",
        "|---|---:|",
        f"| \U0001f7e2 Strong | {level_counts['strong']} |",
        f"| \U0001f7e1 Medium | {level_counts['medium']} |",
        f"| \U0001f7e0 Weak | {level_counts['weak']} |",
        f"| \U0001f534 Insufficient | {level_counts['insufficient']} |",
        "",
        "## Recommended Next Actions",
        "",
        "| Action | Count |",
        "|---|---:|",
    ]
    for action, cnt in sorted(action_counts.items(), key=lambda x: -x[1]):
        lines.append(f"| {_action_label(action)} | {cnt} |")
    lines += ["", "## Truth Scores", ""]

    for i, s in enumerate(sorted(scores, key=lambda x: -x.truth_score), 1):
        lines += [
            f"### {i}. {s.group_title_zh}",
            "",
            f"Truth Score: **{s.truth_score:.1f}** / 100",
            f"Truth Level: {_level_emoji(s.truth_level)} **{s.truth_level}**",
            f"Recommended Next Action: {_action_label(s.recommended_next_action)}",
            f"Evidence Count: {s.evidence_count}",
            f"Source Count: {s.source_count}",
        ]
        if s.personas:
            lines.append(f"Personas: {', '.join(s.personas)}")
        if s.domain_tags:
            lines.append(f"Domain Tags: {', '.join(s.domain_tags)}")
        lines += [
            "",
            "**Dimension Scores:**",
            f"- \u75db\u70b9\u8bc1\u636e\u5f3a\u5ea6 (Pain Evidence Strength): {s.dimension_scores.get('pain_evidence_strength', 0):.1f}",
            f"- \u91cd\u590d\u9891\u7387 (Frequency / Repetition): {s.dimension_scores.get('frequency_repetition', 0):.1f}",
            f"- \u5df2\u6709\u66ff\u4ee3\u65b9\u6848 (Existing Workaround): {s.dimension_scores.get('existing_workaround', 0):.1f}",
            f"- \u4ed8\u8d39\u610f\u613f\u4fe1\u53f7 (Willingness-to-Pay): {s.dimension_scores.get('willingness_to_pay', 0):.1f}",
            f"- \u7528\u6237\u753b\u50cf\u6e05\u6670\u5ea6 (Persona Clarity): {s.dimension_scores.get('persona_clarity', 0):.1f}",
            "",
        ]
        if s.positive_signals:
            lines.append("**Positive Signals:**")
            for sig in s.positive_signals:
                lines.append(f"- {sig}")
            lines.append("")
        if s.negative_signals:
            lines.append("**Negative Signals:**")
            for sig in s.negative_signals:
                lines.append(f"- {sig}")
            lines.append("")
        if s.risk_flags:
            lines.append("**Risk Flags:**")
            for flag in s.risk_flags:
                lines.append(f"- {flag}")
            lines.append("")
        lines += [
            f"**Scoring Reason:** {s.scoring_reason_zh}",
            "",
            f"**Group Summary:** {s.group_summary_zh}",
            "",
            "---",
            "",
        ]

    output_path.write_text("\n".join(lines), encoding="utf-8")


def build_top_truth_candidates_report(
    scores: list[TruthScore],
    output_path: str | Path = "outputs/top_truth_candidates_report.md",
) -> None:
    """Write Top Truth Candidates report (strong + medium only, sorted by score)."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    top = [s for s in scores if s.truth_level in ("strong", "medium")]
    top = sorted(top, key=lambda x: -x.truth_score)

    proceed_count = sum(1 for s in top if s.recommended_next_action == "proceed_to_fit_scoring")
    needs_evidence_count = sum(1 for s in top if s.recommended_next_action == "needs_more_evidence")
    keep_watch_count = sum(1 for s in top if s.recommended_next_action == "keep_watch")

    lines: list[str] = [
        "# Top Truth Candidates Report",
        "",
        "## Summary",
        "",
        f"- Candidates: {len(top)}",
        f"- Proceed to Fit Scoring: {proceed_count}",
        f"- Needs More Evidence: {needs_evidence_count}",
        f"- Keep Watch: {keep_watch_count}",
        "",
        "> \u6ce8\u610f\uff1a\u672c\u62a5\u544a\u5c55\u793a\u7684\u662f\u8bc4\u5206\u8f83\u9ad8\u7684\u9700\u6c42\u7ec4\uff0c",
        "> \u201c\u53ef\u8fdb\u884c Fit Scoring\u201d\u4e0d\u7b49\u4e8e\u201c\u5efa\u8bae\u505a\u4ea7\u54c1\u201d\u3002",
        "",
        "## Top Candidates",
        "",
    ]

    for i, s in enumerate(top, 1):
        positive_summary = "; ".join(s.positive_signals[:3]) if s.positive_signals else "\u6682\u65e0"
        lines += [
            f"### {i}. {s.group_title_zh}",
            "",
            f"Score: **{s.truth_score:.1f}** | Level: {_level_emoji(s.truth_level)} **{s.truth_level}**",
            f"Next Action: {_action_label(s.recommended_next_action)}",
            "",
            f"**Why it looks real:** {s.scoring_reason_zh}",
            f"**Evidence:** {s.evidence_count} items across {s.source_count} sources",
            f"**Key Signals:** {positive_summary}",
        ]
        if s.risk_flags:
            lines.append(f"**Risks:** {', '.join(s.risk_flags)}")
        lines += ["", "---", ""]

    if not top:
        lines.append("\u6682\u65e0\u8fbe\u5230 medium \u4ee5\u4e0a\u7ea7\u522b\u7684\u9700\u6c42\u7ec4\u3002\u5efa\u8bae\u8865\u5145\u66f4\u591a\u8bc1\u636e\u3002")

    output_path.write_text("\n".join(lines), encoding="utf-8")
