"""Stage R1: Real evidence pack validator."""
from __future__ import annotations
import csv
import json
from pathlib import Path
from demand_radar.real_evidence.real_evidence_schema import RealEvidenceItem, RealEvidenceValidation
from demand_radar.real_evidence.source_classifier import classify_source_quality, classify_signal_types
from demand_radar.real_evidence.source_weighting import get_source_weight
from demand_radar.real_evidence.evidence_rubric import score_evidence_strength
from demand_radar.state.raw_store import next_ids, utc_now_iso

TEMPLATE_COLUMNS = [
    "evidence_id", "target_direction_id", "target_direction_title_zh",
    "source_url", "source_note", "source_name", "source_type",
    "source_author_or_org", "published_at", "observed_at", "language",
    "title", "raw_text", "evidence_quote",
    "persona", "persona_confidence", "workflow_stage", "pain_type",
    "evidence_type", "commercial_signal_type",
    "current_solution", "paid_alternative", "business_impact",
    "time_cost_signal", "budget_signal",
    "domain_tags", "collection_query", "collector_note",
    "is_synthetic", "exclude_from_scoring",
]


def generate_template(
    output_path: str | Path = "examples/real_evidence_pack_ai_investment_tracking_template.csv",
) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    example_row = {
        "evidence_id": "re_001",
        "target_direction_id": "ai_investment_tracking",
        "target_direction_title_zh": "\u6295\u8d44\u4eba / \u7814\u7a76\u5458 AI \u4ea7\u4e1a\u8ddf\u8e2a\u4e0e\u9879\u76ee\u521d\u7b5b",
        "source_url": "https://example.com/real-article",
        "source_note": "",
        "source_name": "\u6765\u6e90\u540d\u79f0",
        "source_type": "product_review",
        "source_author_or_org": "",
        "published_at": "2024-01-01",
        "observed_at": "",
        "language": "en",
        "title": "\u6587\u7ae0\u6807\u9898",
        "raw_text": "\u771f\u5b9e\u539f\u6587\u6458\u5f55\uff08\u4e0d\u5c11\u4e8e80\u5b57\u7b26\uff09...",
        "evidence_quote": "\u6700\u5173\u952e\u7684\u4e00\u53e5\u8bdd",
        "persona": "\u6295\u8d44\u4eba",
        "persona_confidence": "0.9",
        "workflow_stage": "sourcing",
        "pain_type": "information_scattered",
        "evidence_type": "pain_signal",
        "commercial_signal_type": "paid_tool",
        "current_solution": "\u73b0\u5728\u7528\u7684\u5de5\u5177\u6216\u65b9\u6cd5",
        "paid_alternative": "\u4ed8\u8d39\u5de5\u5177\u540d\u79f0\u548c\u4ef7\u683c",
        "business_impact": "\u5bf9\u4e1a\u52a1\u7684\u5f71\u54cd",
        "time_cost_signal": "\u65f6\u95f4/\u4eba\u529b\u6210\u672c\u63cf\u8ff0",
        "budget_signal": "\u9884\u7b97/\u6210\u672c\u4fe1\u53f7",
        "domain_tags": "ai|investment|research",
        "collection_query": "\u641c\u7d22\u5173\u952e\u8bcd",
        "collector_note": "\u91c7\u96c6\u5907\u6ce8",
        "is_synthetic": "false",
        "exclude_from_scoring": "false",
    }
    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=TEMPLATE_COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerow(example_row)
    return output_path


def _parse_bool(v) -> bool:
    return str(v).lower().strip() in ("true", "1", "yes")


def validate_real_evidence_pack(
    input_path: str | Path,
    items_output: str | Path = "data/processed/real_evidence_items.jsonl",
    validation_output: str | Path = "data/processed/real_evidence_validation.jsonl",
    min_raw_text_chars: int = 80,
) -> tuple[list[RealEvidenceItem], list[RealEvidenceValidation]]:
    input_path = Path(input_path)
    items_output = Path(items_output)
    validation_output = Path(validation_output)
    items_output.parent.mkdir(parents=True, exist_ok=True)
    validation_output.parent.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        return [], []

    raw_rows: list[dict] = []
    with input_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_rows.append(dict(row))

    val_ids = next_ids("reval", [], len(raw_rows))
    items: list[RealEvidenceItem] = []
    validations: list[RealEvidenceValidation] = []

    for val_id, row in zip(val_ids, raw_rows):
        errors: list[str] = []
        warnings: list[str] = []
        detected: list[str] = []

        raw_text = (row.get("raw_text") or "").strip()
        source_url = (row.get("source_url") or "").strip()
        source_note = (row.get("source_note") or "").strip()
        source_type = (row.get("source_type") or "unknown").strip()
        is_synthetic = _parse_bool(row.get("is_synthetic", "false"))
        exclude = _parse_bool(row.get("exclude_from_scoring", "false"))
        evidence_id = (row.get("evidence_id") or "").strip()

        if not raw_text:
            errors.append("raw_text is empty")
        elif len(raw_text) < min_raw_text_chars:
            errors.append(f"raw_text too short ({len(raw_text)} < {min_raw_text_chars} chars)")

        if not source_url and not source_note:
            errors.append("no source_url and no source_note")

        if is_synthetic and not exclude:
            errors.append("is_synthetic=true requires exclude_from_scoring=true")

        if is_synthetic:
            warnings.append("synthetic sample - will be excluded from scoring")

        if not row.get("persona"):
            warnings.append("persona missing - reduces scoring confidence")

        if not row.get("pain_type") and not row.get("evidence_type"):
            warnings.append("neither pain_type nor evidence_type filled - classify this signal")

        # Source-specific checks
        if source_type == "marketing_article" and not row.get("evidence_quote"):
            warnings.append("marketing_article source without user quote - likely low value")

        # Detect signal types from content
        detected.extend(classify_signal_types(source_type))

        if is_synthetic and exclude:
            status = "excluded"
            include = False
        elif errors:
            status = "invalid"
            include = False
        elif warnings:
            status = "warning"
            include = True
        else:
            status = "valid"
            include = True

        source_quality = classify_source_quality(source_type)
        source_weight = get_source_weight(source_type)

        # Build RealEvidenceItem (skip if invalid)
        if status not in ("invalid", "excluded") or (is_synthetic and exclude):
            domain_tags_raw = row.get("domain_tags", "")
            domain_tags = [t.strip() for t in domain_tags_raw.split("|") if t.strip()] if domain_tags_raw else []
            try:
                pc_raw = row.get("persona_confidence")
                pc = float(pc_raw) if pc_raw and pc_raw.strip() else None
            except (ValueError, TypeError):
                pc = None

            try:
                item = RealEvidenceItem(
                    evidence_id=evidence_id or val_id,
                    target_direction_id=row.get("target_direction_id", "ai_investment_tracking"),
                    target_direction_title_zh=row.get("target_direction_title_zh", ""),
                    source_url=source_url or None,
                    source_note=source_note or None,
                    source_name=row.get("source_name") or None,
                    source_type=source_type,
                    source_author_or_org=row.get("source_author_or_org") or None,
                    published_at=row.get("published_at") or None,
                    observed_at=row.get("observed_at") or None,
                    language=row.get("language") or "zh",
                    title=row.get("title") or None,
                    raw_text=raw_text or "placeholder",
                    evidence_quote=row.get("evidence_quote") or None,
                    persona=row.get("persona") or None,
                    persona_confidence=pc,
                    workflow_stage=row.get("workflow_stage") or None,
                    pain_type=row.get("pain_type") or None,
                    evidence_type=row.get("evidence_type") or None,
                    commercial_signal_type=row.get("commercial_signal_type") or None,
                    current_solution=row.get("current_solution") or None,
                    paid_alternative=row.get("paid_alternative") or None,
                    business_impact=row.get("business_impact") or None,
                    time_cost_signal=row.get("time_cost_signal") or None,
                    budget_signal=row.get("budget_signal") or None,
                    domain_tags=domain_tags,
                    collection_query=row.get("collection_query") or None,
                    collector_note=row.get("collector_note") or None,
                    is_synthetic=is_synthetic,
                    exclude_from_scoring=exclude,
                    created_at=utc_now_iso(),
                )
                items.append(item)
            except Exception as e:
                errors.append(f"schema error: {e}")
                status = "invalid"
                include = False

        validations.append(RealEvidenceValidation(
            validation_id=val_id,
            evidence_id=evidence_id or val_id,
            status=status,
            source_quality=source_quality,
            validation_errors=errors,
            validation_warnings=warnings,
            detected_signal_types=detected,
            source_weight=source_weight,
            include_in_pipeline=include,
            created_at=utc_now_iso(),
        ))

    # Write outputs
    items_output.write_text(
        "\n".join(i.model_dump_json() for i in items) + "\n",
        encoding="utf-8",
    )
    validation_output.write_text(
        "\n".join(v.model_dump_json() for v in validations) + "\n",
        encoding="utf-8",
    )
    return items, validations
