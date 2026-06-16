"""Radar pipeline: ties acquisition -> evidence draft -> R1 validation -> report."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timezone

from .acquisition_pipeline import run_acquisition
from .evidence_pack_draft_builder import build_evidence_pack_draft
from .acquisition_report import build_acquisition_report, build_evidence_pack_draft_report
from .acquisition_store import load_evidence_candidates


_RADAR_REPORT = Path("outputs/radar/radar_report.md")


@dataclass
class RadarRunSummary:
    run_id: str
    domain_id: str
    raw_signals: int
    unique_signals: int
    duplicates: int
    candidates: int
    valid_candidates: int
    draft_csv: Path | None
    r1_validation_summary: dict
    errors: list[str]
    warnings: list[str]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_radar(
    domain_id: str,
    domain_config_dir: Path | None = None,
    source_registry_path: Path | None = None,
    draft_output: Path | None = None,
    radar_report_path: Path | None = None,
    skip_r1_validation: bool = False,
) -> RadarRunSummary:
    """Full radar pipeline: acquisition -> draft -> R1 validation -> report."""

    # Step 1: acquisition
    summary, candidates = run_acquisition(
        domain_id=domain_id,
        domain_config_dir=domain_config_dir,
        source_registry_path=source_registry_path,
    )

    # Step 2: build acquisition report
    build_acquisition_report(summary, candidates)

    # Step 3: build evidence pack draft
    draft_path = build_evidence_pack_draft(candidates, draft_output)

    # Step 4: build draft report
    build_evidence_pack_draft_report(candidates, draft_path)

    # Step 5: R1 validation on draft (if file exists and not skipped)
    r1_summary: dict = {"status": "skipped", "items": 0, "valid": 0, "warning": 0, "invalid": 0}
    if not skip_r1_validation and draft_path.exists():
        try:
            from demand_radar.real_evidence.real_evidence_validator import validate_real_evidence_pack
            from pathlib import Path as _Path
            items_out = _Path("data/processed/acquisition/r1_items.jsonl")
            val_out = _Path("data/processed/acquisition/r1_validation.jsonl")
            items, validations = validate_real_evidence_pack(draft_path, items_out, val_out)
            r1_summary = {
                "status": "ran",
                "items": len(items),
                "valid": sum(1 for v in validations if v.status == "valid"),
                "warning": sum(1 for v in validations if v.status == "warning"),
                "invalid": sum(1 for v in validations if v.status == "invalid"),
            }
        except Exception as exc:
            r1_summary = {"status": "error", "error": str(exc)}

    # Step 6: build radar report
    _build_radar_report(
        summary=summary,
        candidates=candidates,
        draft_path=draft_path,
        r1_summary=r1_summary,
        output_path=radar_report_path,
    )

    return RadarRunSummary(
        run_id=summary.run_id,
        domain_id=domain_id,
        raw_signals=summary.raw_signal_count,
        unique_signals=summary.unique_signal_count,
        duplicates=summary.duplicate_count,
        candidates=summary.evidence_candidate_count,
        valid_candidates=summary.valid_candidate_count,
        draft_csv=draft_path,
        r1_validation_summary=r1_summary,
        errors=summary.errors,
        warnings=summary.warnings,
    )


def _build_radar_report(
    summary,
    candidates,
    draft_path: Path,
    r1_summary: dict,
    output_path: Path | None = None,
) -> Path:
    out = output_path or _RADAR_REPORT
    out.parent.mkdir(parents=True, exist_ok=True)
    valid_cands = [c for c in candidates if c.include_in_evidence_pack]
    next_action = "Proceed to fill evidence pack fields (persona, pain_type, evidence_quote)"
    if summary.valid_candidate_count >= 15:
        next_action = "Good coverage - fill fields and run demand-radar run-stage-r1"
    elif summary.valid_candidate_count >= 5:
        next_action = "Partial coverage - consider more sources or add manual seed URLs"
    else:
        next_action = "Low coverage - add more search queries or manual seed URLs"

    lines = [
        "# Radar Run Report",
        "",
        f"- Domain: {summary.domain_id}",
        f"- Run ID: {summary.run_id}",
        f"- Generated at: {_now()}",
        "",
        "## Source Summary",
        "",
        f"- Raw signals fetched: {summary.raw_signal_count}",
        f"- Unique signals: {summary.unique_signal_count}",
        f"- Duplicates removed: {summary.duplicate_count}",
        "",
        "## Candidate Summary",
        "",
        f"- Total candidates: {summary.evidence_candidate_count}",
        f"- Valid: {summary.valid_candidate_count}",
        f"- Warning: {summary.warning_candidate_count}",
        f"- Invalid: {summary.invalid_candidate_count}",
        "",
        "## Evidence Pack Draft",
        "",
        f"- Draft CSV: {draft_path}",
        f"- Items in draft: {len(valid_cands)}",
        "",
        "## R1 Validation",
        "",
    ]
    for k, v in r1_summary.items():
        lines.append(f"- {k}: {v}")

    if summary.errors:
        lines += ["", "## Errors", ""]
        for e in summary.errors[:10]:
            lines.append(f"- {e}")

    lines += ["", "## Recommended Next Action", "", f"> {next_action}", ""]
    out.write_text("\n".join(lines), encoding="utf-8")
    return out
