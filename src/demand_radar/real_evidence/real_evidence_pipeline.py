"""Stage R1: real_evidence_pipeline - orchestrates the full R1 flow."""
from __future__ import annotations
import csv
from pathlib import Path
from datetime import datetime, timezone

from demand_radar.real_evidence.real_evidence_validator import (
    generate_template,
    validate_real_evidence_pack,
)
from demand_radar.real_evidence.real_evidence_store import (
    write_real_evidence_items,
    write_real_evidence_validations,
    load_calibration_reviews,
    load_calibration_findings,
)
from demand_radar.real_evidence.calibration_report import (
    build_real_evidence_pack_report,
    build_calibration_report,
    build_prompt_skill_recommendations,
)

_TEMPLATE_PATH = Path("examples/real_evidence_pack_ai_investment_tracking_template.csv")
_FILLED_PATH = Path("examples/real_evidence_pack_ai_investment_tracking.csv")
_SIGNAL_OUTPUT = Path("examples/real_evidence_signals_ai_investment_tracking.csv")


def convert_to_signal_csv(items, output_path: Path | None = None) -> Path:
    """Convert RealEvidenceItems to signal CSV format compatible with run-stage26."""
    out = output_path or _SIGNAL_OUTPUT
    out.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "title", "raw_text", "url", "source_name", "source_type",
        "published_at", "language", "domain_tags", "batch_id",
        "source_note", "signal_focus", "expected_quality",
    ]

    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for item in items:
            domain_tags = "|".join(item.domain_tags) if item.domain_tags else "ai_investment_research"
            writer.writerow({
                "title": item.title or item.evidence_id,
                "raw_text": item.raw_text,
                "url": item.source_url or "",
                "source_name": item.source_name or item.source_type,
                "source_type": item.source_type,
                "published_at": item.published_at or "",
                "language": item.language,
                "domain_tags": domain_tags,
                "batch_id": "batch_stage_r1_real_evidence",
                "source_note": item.source_note or "",
                "signal_focus": item.evidence_type or "pain",
                "expected_quality": "strong" if item.source_type in (
                    "product_review", "community_discussion", "github_issue",
                    "interview_note", "case_study",
                ) else "medium",
            })
    return out


def run_stage_r1(
    template_path: Path | None = None,
    filled_path: Path | None = None,
    skip_llm: bool = True,
) -> dict:
    """Orchestrate the full Stage R1 flow."""
    tpl = template_path or _TEMPLATE_PATH
    filled = filled_path or _FILLED_PATH

    result: dict = {
        "template_generated": False,
        "filled_file_exists": False,
        "items": 0,
        "valid": 0,
        "warning": 0,
        "invalid": 0,
        "excluded": 0,
        "signal_csv_generated": False,
        "reports_generated": [],
    }

    # Step 1: Generate template if missing
    if not tpl.exists():
        generate_template(tpl)
        result["template_generated"] = True

    # Step 2: Check filled file
    if not filled.exists():
        print(
            f"[Stage R1] 真实证据包尚未填写。请先填写：{filled}\n"
            "可参考模板：" + str(tpl)
        )
        return result

    result["filled_file_exists"] = True

    # Step 3: Validate
    items_path = Path("data/processed/real_evidence_items.jsonl")
    validation_path = Path("data/processed/real_evidence_validation.jsonl")
    items, validations = validate_real_evidence_pack(filled, items_path, validation_path)

    write_real_evidence_items(items)
    write_real_evidence_validations(validations)

    result["items"] = len(items)
    result["valid"] = sum(1 for v in validations if v.status == "valid")
    result["warning"] = sum(1 for v in validations if v.status == "warning")
    result["invalid"] = sum(1 for v in validations if v.status == "invalid")
    result["excluded"] = sum(1 for v in validations if v.status == "excluded")

    # Step 4: Convert to signal CSV
    includeable = [i for i, v in zip(items, validations) if v.include_in_pipeline]
    if includeable:
        convert_to_signal_csv(includeable)
        result["signal_csv_generated"] = True

    # Step 5: Build reports
    pack_report = build_real_evidence_pack_report(items, validations)
    result["reports_generated"].append(str(pack_report))

    reviews = load_calibration_reviews()
    cal_report = build_calibration_report(reviews)
    result["reports_generated"].append(str(cal_report))

    findings = load_calibration_findings()
    rec_report = build_prompt_skill_recommendations(reviews, findings)
    result["reports_generated"].append(str(rec_report))

    return result