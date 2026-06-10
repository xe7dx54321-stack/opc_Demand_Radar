"""Pain points report writer."""

from __future__ import annotations

import json
from pathlib import Path

from demand_radar.config.schemas import PainPoint, RunSummary
from demand_radar.state.processed_store import load_normalized_signals, load_pain_points
from demand_radar.state.quarantine_store import load_quarantine
from demand_radar.state.raw_store import load_raw_signals, utc_now_iso


def build_pain_points_report(
    raw_path: str | Path = "data/raw/raw_signals.jsonl",
    normalized_path: str | Path = "data/processed/normalized_signals.jsonl",
    pain_points_path: str | Path = "data/processed/pain_points.jsonl",
    quarantine_path: str | Path = "data/quarantine/invalid_outputs.jsonl",
    report_path: str | Path = "outputs/pain_points_report.md",
    summary_path: str | Path = "outputs/run_summary.json",
) -> RunSummary:
    raw_signals = load_raw_signals(raw_path)
    normalized_signals = load_normalized_signals(normalized_path)
    pain_points = load_pain_points(pain_points_path)
    quarantine_records = load_quarantine(quarantine_path)
    summary = RunSummary(
        raw_signals=len(raw_signals),
        normalized_signals=len(normalized_signals),
        pain_points=len(pain_points),
        quarantined_items=len(quarantine_records),
        generated_at=utc_now_iso(),
    )

    _write_markdown(pain_points, summary, report_path)
    _write_summary(summary, summary_path)
    return summary


def _write_markdown(
    pain_points: list[PainPoint],
    summary: RunSummary,
    report_path: str | Path,
) -> None:
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Pain Points Report",
        "",
        "## Run Summary",
        "",
        f"- Raw signals: {summary.raw_signals}",
        f"- Normalized signals: {summary.normalized_signals}",
        f"- Extracted pain points: {summary.pain_points}",
        f"- Quarantined items: {summary.quarantined_items}",
        f"- Generated at: {summary.generated_at}",
        "",
        "## Pain Points",
        "",
    ]
    if not pain_points:
        lines.append("No valid pain points extracted.")
    for index, pain_point in enumerate(pain_points, start=1):
        lines.extend(_pain_point_lines(index, pain_point))
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _pain_point_lines(index: int, pain_point: PainPoint) -> list[str]:
    source = pain_point.normalized_signal_id
    return [
        f"### {index}. {pain_point.pain_point_id}",
        "",
        f"Persona: {pain_point.persona or ''}",
        f"Scenario: {pain_point.scenario or ''}",
        f"Job to be done: {pain_point.job_to_be_done or ''}",
        f"Pain: {pain_point.pain_description}",
        f"Current workaround: {pain_point.current_workaround or ''}",
        f"Frequency signal: {pain_point.frequency_signal or ''}",
        f"Payment signal: {pain_point.payment_signal or ''}",
        f"Confidence: {pain_point.confidence:.2f}",
        f"Source: raw={pain_point.raw_signal_id}, normalized={source}",
        f"Evidence quote: {pain_point.evidence_quote}",
        "",
        "---",
        "",
    ]


def _write_summary(summary: RunSummary, summary_path: str | Path) -> None:
    summary_path = Path(summary_path)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
