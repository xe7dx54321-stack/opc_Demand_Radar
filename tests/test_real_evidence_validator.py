"""Tests for real_evidence_validator module."""
from __future__ import annotations
import csv
from pathlib import Path
import pytest
from demand_radar.real_evidence.real_evidence_validator import (
    generate_template,
    validate_real_evidence_pack,
    TEMPLATE_COLUMNS,
)


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=TEMPLATE_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in TEMPLATE_COLUMNS})


def _valid_row(**overrides):
    row = {
        "evidence_id": "re_test_001",
        "target_direction_id": "ai_investment_tracking",
        "target_direction_title_zh": "AI 产业跟踪",
        "source_url": "https://example.com/review",
        "source_note": "",
        "source_name": "G2",
        "source_type": "product_review",
        "source_author_or_org": "",
        "published_at": "2024-01-01",
        "observed_at": "",
        "language": "en",
        "title": "Test Review",
        "raw_text": "We spend hours manually tracking AI companies. The process is inefficient and costly.",
        "evidence_quote": "hours manually tracking AI companies",
        "persona": "investor",
        "persona_confidence": "0.9",
        "workflow_stage": "sourcing",
        "pain_type": "information_scattered",
        "evidence_type": "pain_signal",
        "commercial_signal_type": "paid_tool",
        "current_solution": "manual spreadsheet",
        "paid_alternative": "PitchBook",
        "business_impact": "2-3 hours per week wasted",
        "time_cost_signal": "2-3 hours weekly",
        "budget_signal": "$200/month",
        "domain_tags": "ai_investment_research",
        "collection_query": "AI deal sourcing pain",
        "collector_note": "",
        "is_synthetic": "false",
        "exclude_from_scoring": "false",
    }
    row.update(overrides)
    return row


def test_generate_template(tmp_path):
    out = tmp_path / "template.csv"
    result = generate_template(out)
    assert result.exists()
    with open(result, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) >= 1


def test_template_has_all_columns(tmp_path):
    out = tmp_path / "template.csv"
    generate_template(out)
    with open(out, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames or []
    # Strip BOM from first column if present (utf-8-sig)
    cols = [c.lstrip("\ufeff") for c in cols]
    for col in TEMPLATE_COLUMNS:
        assert col in cols


def test_valid_row_passes(tmp_path):
    csv_path = tmp_path / "evidence.csv"
    items_path = tmp_path / "items.jsonl"
    val_path = tmp_path / "val.jsonl"
    _write_csv(csv_path, [_valid_row()])
    items, validations = validate_real_evidence_pack(csv_path, items_path, val_path)
    assert len(validations) == 1
    assert validations[0].status in ("valid", "warning")


def test_missing_source_url_and_note_is_invalid(tmp_path):
    csv_path = tmp_path / "evidence.csv"
    items_path = tmp_path / "items.jsonl"
    val_path = tmp_path / "val.jsonl"
    _write_csv(csv_path, [_valid_row(source_url="", source_note="")])
    items, validations = validate_real_evidence_pack(csv_path, items_path, val_path)
    assert validations[0].status == "invalid"


def test_short_raw_text_is_invalid(tmp_path):
    csv_path = tmp_path / "evidence.csv"
    items_path = tmp_path / "items.jsonl"
    val_path = tmp_path / "val.jsonl"
    _write_csv(csv_path, [_valid_row(raw_text="Too short.")])
    items, validations = validate_real_evidence_pack(csv_path, items_path, val_path)
    assert validations[0].status == "invalid"


def test_synthetic_without_exclude_is_invalid(tmp_path):
    csv_path = tmp_path / "evidence.csv"
    items_path = tmp_path / "items.jsonl"
    val_path = tmp_path / "val.jsonl"
    _write_csv(csv_path, [_valid_row(is_synthetic="true", exclude_from_scoring="false")])
    items, validations = validate_real_evidence_pack(csv_path, items_path, val_path)
    assert validations[0].status == "invalid"


def test_synthetic_with_exclude_is_excluded(tmp_path):
    csv_path = tmp_path / "evidence.csv"
    items_path = tmp_path / "items.jsonl"
    val_path = tmp_path / "val.jsonl"
    _write_csv(csv_path, [_valid_row(is_synthetic="true", exclude_from_scoring="true")])
    items, validations = validate_real_evidence_pack(csv_path, items_path, val_path)
    assert validations[0].status == "excluded"


def test_output_files_created(tmp_path):
    csv_path = tmp_path / "evidence.csv"
    items_path = tmp_path / "items.jsonl"
    val_path = tmp_path / "val.jsonl"
    _write_csv(csv_path, [_valid_row()])
    validate_real_evidence_pack(csv_path, items_path, val_path)
    assert items_path.exists()
    assert val_path.exists()