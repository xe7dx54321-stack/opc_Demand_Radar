"""Build markdown reports for acquisition runs."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path

from .acquisition_schema import AcquisitionRunSummary, EvidenceCandidate

_ACQ_REPORT = Path("outputs/acquisition/acquisition_report.md")
_DRAFT_REPORT = Path("outputs/acquisition/evidence_pack_draft_report.md")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_acquisition_report(
    summary: AcquisitionRunSummary,
    candidates: list[EvidenceCandidate],
    output_path: Path | None = None,
) -> Path:
    out = output_path or _ACQ_REPORT
    out.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Acquisition Report",
        "",
        f"## Run: {summary.run_id}",
        "",
        f"- Domain: {summary.domain_id}",
        f"- Started: {summary.started_at}",
        f"- Ended: {summary.ended_at or _now()}",
        "",
        "## Signal Summary",
        "",
        f"- Raw signals: {summary.raw_signal_count}",
        f"- Unique signals: {summary.unique_signal_count}",
        f"- Duplicates: {summary.duplicate_count}",
        f"- Evidence candidates: {summary.evidence_candidate_count}",
        f"- Valid: {summary.valid_candidate_count}",
        f"- Warning: {summary.warning_candidate_count}",
        f"- Invalid: {summary.invalid_candidate_count}",
        "",
        "## By Source",
        "",
    ]
    for src, cnt in summary.by_source.items():
        lines.append(f"- {src}: {cnt}")

    lines += ["", "## By Source Type", ""]
    for stype, cnt in summary.by_source_type.items():
        lines.append(f"- {stype}: {cnt}")

    if summary.errors:
        lines += ["", "## Errors", ""]
        for e in summary.errors:
            lines.append(f"- {e}")

    if summary.warnings:
        lines += ["", "## Warnings", ""]
        for w in summary.warnings:
            lines.append(f"- {w}")

    # Top candidates
    top = [c for c in candidates if c.include_in_evidence_pack][:10]
    if top:
        lines += ["", "## Top Evidence Candidates", ""]
        for c in top:
            lines += [
                f"### {c.candidate_id}",
                f"- Source: {c.source_type} | {c.source_url or 'N/A'}",
                f"- Title: {c.title or 'N/A'}",
                f"- Status: {c.validation_status}",
                f"- Signal types: {', '.join(c.detected_signal_types) or 'none'}",
                f"- Text excerpt: {c.raw_text[:120]}...",
                "",
            ]

    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def build_evidence_pack_draft_report(
    candidates: list[EvidenceCandidate],
    draft_path: Path,
    output_path: Path | None = None,
) -> Path:
    out = output_path or _DRAFT_REPORT
    out.parent.mkdir(parents=True, exist_ok=True)

    valid = [c for c in candidates if c.include_in_evidence_pack]
    pay = sum(1 for c in valid if "paid_signal" in c.detected_signal_types)
    work = sum(1 for c in valid if "workaround_signal" in c.detected_signal_types)
    flow = sum(1 for c in valid if "workflow_signal" in c.detected_signal_types)

    lines = [
        "# Evidence Pack Draft Report",
        "",
        f"- Draft CSV: {draft_path}",
        f"- Total candidates: {len(candidates)}",
        f"- Included in draft: {len(valid)}",
        f"- Paid/cost signals: {pay}",
        f"- Workaround signals: {work}",
        f"- Workflow signals: {flow}",
        f"- Generated at: {_now()}",
        "",
        "## Next Steps",
        "",
        "1. Review draft CSV: " + str(draft_path),
        "2. Fill in business fields: persona, workflow_stage, pain_type, evidence_quote",
        "3. Run: demand-radar validate-real-evidence-pack --input " + str(draft_path),
        "4. Run: demand-radar run-stage-r1",
        "",
    ]
    out.write_text("\n".join(lines), encoding="utf-8")
    return out
