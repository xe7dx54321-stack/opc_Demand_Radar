"""Calibration report generation for Stage 1.5."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from demand_radar.calibration.calibration_review import load_calibration_reviews
from demand_radar.calibration.calibration_schema import VALID_REVIEW_LABELS, CalibrationReview
from demand_radar.config.load_config import load_yaml
from demand_radar.config.schemas import RunSummary
from demand_radar.state.processed_store import load_normalized_signals, load_pain_points
from demand_radar.state.quarantine_store import load_quarantine
from demand_radar.state.raw_store import load_raw_signals, utc_now_iso


QUALITY_LABELS = [
    "good_extraction",
    "weak_extraction",
    "false_positive",
    "false_negative",
    "bad_quote",
    "bad_persona",
    "should_quarantine",
]


def build_calibration_report(
    raw_path: str | Path = "data/raw/raw_signals.jsonl",
    normalized_path: str | Path = "data/processed/normalized_signals.jsonl",
    pain_points_path: str | Path = "data/processed/pain_points.jsonl",
    quarantine_path: str | Path = "data/quarantine/invalid_outputs.jsonl",
    reviews_path: str | Path = "data/processed/calibration_reviews.jsonl",
    report_path: str | Path = "outputs/calibration_report.md",
    summary_path: str | Path = "outputs/run_summary.json",
    calibration_config_path: str | Path = "configs/calibration_config.yaml",
) -> RunSummary:
    raw_signals = load_raw_signals(raw_path)
    normalized_signals = load_normalized_signals(normalized_path)
    pain_points = load_pain_points(pain_points_path)
    quarantine_records = load_quarantine(quarantine_path)
    reviews = load_calibration_reviews(reviews_path)
    config = _safe_load_config(calibration_config_path)
    summary = RunSummary(
        raw_signals=len(raw_signals),
        normalized_signals=len(normalized_signals),
        pain_points=len(pain_points),
        quarantined_items=len(quarantine_records),
        calibration_reviews=len(reviews),
        generated_at=utc_now_iso(),
    )

    _write_markdown(reviews, summary, config, report_path)
    _write_summary(summary, summary_path)
    return summary


def _safe_load_config(path: str | Path) -> dict[str, object]:
    path = Path(path)
    if not path.exists():
        return {}
    return load_yaml(path)


def _write_markdown(
    reviews: list[CalibrationReview],
    summary: RunSummary,
    config: dict[str, object],
    report_path: str | Path,
) -> None:
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    counts = Counter(review.label for review in reviews)
    max_examples = int(
        ((config.get("calibration") or {}).get("report") or {}).get("max_examples_per_label", 10)
        if isinstance(config.get("calibration"), dict)
        else 10
    )

    lines = [
        "# Extraction Calibration Report",
        "",
        "## Run Summary",
        "",
        f"- Raw signals: {summary.raw_signals}",
        f"- Normalized signals: {summary.normalized_signals}",
        f"- Pain points: {summary.pain_points}",
        f"- Quarantined items: {summary.quarantined_items}",
        f"- Calibration reviews: {summary.calibration_reviews}",
        f"- Generated at: {summary.generated_at}",
        "",
        "## Extraction Quality Overview",
        "",
    ]
    for label in QUALITY_LABELS:
        lines.append(f"- {_label_title(label)}: {counts[label]}")
    lines.extend(["", "## Review Breakdown", ""])

    for label in sorted(VALID_REVIEW_LABELS):
        label_reviews = [review for review in reviews if review.label == label]
        lines.extend(_review_group_lines(label, label_reviews, max_examples))

    lines.extend(_suggested_rule_improvements(counts))
    lines.extend(_next_step_readiness(summary, counts))
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _review_group_lines(label: str, reviews: list[CalibrationReview], max_examples: int) -> list[str]:
    lines = [f"### {label}", f"- count: {len(reviews)}", "- examples:"]
    if not reviews:
        lines.append("  - None")
    for review in reviews[:max_examples]:
        target = review.pain_point_id or review.normalized_signal_id or review.raw_signal_id
        lines.append(f"  - {review.review_id} ({target}): {review.reviewer_note}")
    lines.append("")
    return lines


def _suggested_rule_improvements(counts: Counter[str]) -> list[str]:
    keyword_additions = "Review false_negative notes for missing domain phrases." if counts["false_negative"] else "None yet."
    keyword_removals = "Review false_positive notes for over-broad keywords." if counts["false_positive"] else "None yet."
    persona_rules = "Review bad_persona notes for persona keyword gaps." if counts["bad_persona"] else "None yet."
    state_gate = "Keep evidence quote and confidence gates strict."
    llm_requirements = (
        "LLM extractor must preserve exact quotes and return empty lists for unsupported pain points."
    )

    return [
        "## Suggested Rule Improvements",
        "",
        f"- keyword additions: {keyword_additions}",
        f"- keyword removals: {keyword_removals}",
        f"- persona rule improvements: {persona_rules}",
        f"- state gate improvements: {state_gate}",
        f"- LLM extractor requirements: {llm_requirements}",
        "",
    ]


def _next_step_readiness(summary: RunSummary, counts: Counter[str]) -> list[str]:
    blocking_issues: list[str] = []
    if summary.calibration_reviews == 0:
        blocking_issues.append("No human calibration reviews recorded yet.")
    if counts["bad_quote"]:
        blocking_issues.append("Bad quote examples need prompt or quote extraction fixes.")
    if counts["false_positive"]:
        blocking_issues.append("False positives need stricter extraction rules.")

    ready = "no" if blocking_issues else "yes"
    issues = "; ".join(blocking_issues) if blocking_issues else "None."
    return [
        "## Next-Step Readiness",
        "",
        f"- Ready for LLM extractor: {ready}",
        f"- Blocking issues: {issues}",
        "- Recommended next phase: Add real structured LLM extraction only after reviewing calibration notes.",
        "",
    ]


def _label_title(label: str) -> str:
    return label.replace("_", " ").capitalize()


def _write_summary(summary: RunSummary, summary_path: str | Path) -> None:
    summary_path = Path(summary_path)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
