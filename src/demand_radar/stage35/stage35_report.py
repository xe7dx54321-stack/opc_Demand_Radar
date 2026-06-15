"""Stage 3.5 report generation."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _g(obj, key, default="N/A"):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def build_stage35_expansion_report(
    run_summary,
    selected_candidates: list,
    validations: list,
    output_path="outputs/stage35_targeted_expansion_report.md",
) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sm = run_summary or {}
    valid_n = sum(1 for v in validations if _g(v, "status") == "valid")
    warn_n = sum(1 for v in validations if _g(v, "status") == "warning")
    inv_n = sum(1 for v in validations if _g(v, "status") == "invalid")

    lines = [
        "# Stage 3.5 Targeted Evidence Expansion Report",
        "",
        "## Summary",
        "",
        f"- Before Snapshot: {_g(sm, 'before_snapshot_name')}",
        f"- Baseline Quality: {_g(sm, 'lineage_baseline_quality')}",
        f"- Selected Candidates: {_g(sm, 'selected_candidates', len(selected_candidates))}",
        f"- Template Rows: {_g(sm, 'template_rows', 0)}",
        f"- Filled Signals: {_g(sm, 'filled_signals', 0)}",
        f"- Valid: {_g(sm, 'valid_signals', valid_n)} Warning: {_g(sm, 'warning_signals', warn_n)} Invalid: {_g(sm, 'invalid_signals', inv_n)}",
        f"- Combined Rows: {_g(sm, 'combined_rows', 0)}",
        f"- Payment/Cost Signals: {_g(sm, 'payment_or_cost_signals', 0)}",
        f"- Stage 4 Gate Status: {_g(sm, 'stage4_gate_status', 'not_run')}",
        f"- Generated at: {_now()}",
        "",
        "## Selected Candidates",
    ]

    for i, cand in enumerate(selected_candidates, start=1):
        intents = ", ".join(_g(cand, "target_evidence_intents") or [])
        lines += [
            "",
            f"### {i}. {_g(cand, 'group_title_zh')}",
            "",
            f"Current Score: {_g(cand, 'current_truth_score')}",
            f"Current Level: {_g(cand, 'current_truth_level')}",
            f"Selected Reason: {_g(cand, 'selected_reason_zh')}",
            f"Target New Signals: {_g(cand, 'target_new_signals')}",
            f"Target Evidence Intents: {intents}",
        ]

    lines += ["", "## Validation Summary", ""]
    if not validations:
        lines.append("No signals validated yet.")
    else:
        lines += [f"- Valid: {valid_n}", f"- Warning: {warn_n}", f"- Invalid: {inv_n}"]
        issues = [v for v in validations if _g(v, "validation_errors")]
        if issues:
            lines += ["", "### Validation Errors"]
            for v in issues[:10]:
                errs = "; ".join(_g(v, "validation_errors") or [])
                lines.append(f"- {_g(v, 'target_signal_id')}: {errs}")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_stage35_stable_delta_report(
    stable_deltas: list,
    output_path="outputs/stage35_stable_delta_report.md",
) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    high_n = sum(1 for d in stable_deltas if _g(d, "delta_confidence") == "high")
    med_n = sum(1 for d in stable_deltas if _g(d, "delta_confidence") == "medium")
    imp_n = sum(1 for d in stable_deltas if (_g(d, "stable_delta") or 0) > 0)

    lines = [
        "# Stage 3.5 Stable Truth Score Delta Report",
        "", "## Summary", "",
        f"- Compared: {len(stable_deltas)} | High: {high_n} | Medium: {med_n} | Improved: {imp_n}",
        f"- Generated at: {_now()}",
        "", "## Stable Deltas",
    ]

    for d in stable_deltas:
        title = _g(d, "after_group_title_zh") or _g(d, "before_group_title_zh") or "N/A"
        drift = ", ".join(_g(d, "drift_flags") or [])
        lines += [
            "", f"### {title}", "",
            f"Before: {_g(d, 'before_truth_score')} | After: {_g(d, 'after_truth_score')} | Delta: {_g(d, 'stable_delta')}",
            f"Confidence: {_g(d, 'delta_confidence')} | Drift: {drift}",
            f"Next Action: {_g(d, 'recommended_next_action')}",
        ]

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_stage35_gate_report(
    gate_result,
    output_path="outputs/stage35_stage4_gate_report.md",
) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    gr = gate_result or {}
    status = _g(gr, "status", "blocked")

    lines = [
        "# Stage 4 Gate Report (Stage 3.5)",
        "", "## Gate Result", "",
        f"Status: **{status}**",
        f"Reason: {_g(gr, 'reason_zh')}",
        f"Required Next Action: {_g(gr, 'required_next_action_zh')}",
        f"Generated at: {_now()}",
        "", "## Formal Fit Scoring Eligibility", "",
    ]

    eligible = _g(gr, "eligible_candidates") or []
    lines += [f"- {c}" for c in eligible] if eligible else ["None."]
    lines += ["", "## Tentative Fit Scoring Eligibility", ""]
    tentative = _g(gr, "tentative_candidates") or []
    lines += [f"- {c}" for c in tentative] if tentative else ["None."]
    lines += ["", "## Blocked Candidates", ""]
    blocked = _g(gr, "blocked_candidates") or []
    lines += [f"- {c}" for c in blocked] if blocked else ["None."]

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
