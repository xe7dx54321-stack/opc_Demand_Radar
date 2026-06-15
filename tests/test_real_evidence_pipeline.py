"""Tests for real_evidence_pipeline module."""
from __future__ import annotations
import csv
from pathlib import Path
import pytest
from demand_radar.real_evidence.real_evidence_validator import TEMPLATE_COLUMNS
from demand_radar.real_evidence.real_evidence_pipeline import (
    convert_to_signal_csv,
    run_stage_r1,
)
from demand_radar.real_evidence.real_evidence_schema import RealEvidenceItem
from demand_radar.state.raw_store import utc_now_iso


def _make_item(**overrides):
    defaults = dict(
        evidence_id="re_001",
        target_direction_id="ai_investment_tracking",
        target_direction_title_zh="AI 产业跟踪",
        source_url="https://example.com",
        source_type="product_review",
        language="en",
        raw_text="We spend hours manually tracking AI startups. The manual process is slow and error-prone.",
        is_synthetic=False,
        exclude_from_scoring=False,
        domain_tags=["ai_investment_research"],
        created_at=utc_now_iso(),
    )
    defaults.update(overrides)
    return RealEvidenceItem(**defaults)


def test_convert_to_signal_csv(tmp_path):
    item = _make_item()
    out = tmp_path / "signals.csv"
    result = convert_to_signal_csv([item], out)
    assert result.exists()
    with open(result, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["raw_text"] == item.raw_text
    assert rows[0]["source_type"] == "product_review"
    assert rows[0]["batch_id"] == "batch_stage_r1_real_evidence"


def test_signal_csv_has_expected_columns(tmp_path):
    item = _make_item()
    out = tmp_path / "signals.csv"
    convert_to_signal_csv([item], out)
    with open(out, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames or []
    for expected_col in ("title", "raw_text", "url", "source_name", "source_type",
                         "published_at", "language", "domain_tags", "batch_id"):
        assert expected_col in cols


def test_run_stage_r1_graceful_when_no_filled_file(tmp_path):
    """run_stage_r1 should not fail when the filled file doesn't exist."""
    template = tmp_path / "template.csv"
    filled = tmp_path / "filled.csv"
    result = run_stage_r1(template_path=template, filled_path=filled)
    assert result["filled_file_exists"] is False
    assert result["items"] == 0


def test_run_stage_r1_with_sample_file(tmp_path):
    """run_stage_r1 should run when filled file exists."""
    template = tmp_path / "template.csv"
    filled = tmp_path / "filled.csv"

    # Create a minimal valid evidence CSV
    rows = [{
        "evidence_id": "re_001",
        "target_direction_id": "ai_investment_tracking",
        "target_direction_title_zh": "AI 产业跟踪",
        "source_url": "https://example.com",
        "source_note": "",
        "source_name": "G2",
        "source_type": "product_review",
        "source_author_or_org": "",
        "published_at": "2024-01-01",
        "observed_at": "",
        "language": "en",
        "title": "Test",
        "raw_text": "We spend 3 hours weekly tracking AI companies manually with spreadsheets. Very inefficient.",
        "evidence_quote": "3 hours weekly tracking AI companies manually",
        "persona": "investor",
        "persona_confidence": "0.9",
        "workflow_stage": "sourcing",
        "pain_type": "information_scattered",
        "evidence_type": "pain_signal",
        "commercial_signal_type": "paid_tool",
        "current_solution": "manual spreadsheet",
        "paid_alternative": "PitchBook",
        "business_impact": "time wasted",
        "time_cost_signal": "3 hours weekly",
        "budget_signal": "$200/month",
        "domain_tags": "ai_investment_research",
        "collection_query": "",
        "collector_note": "",
        "is_synthetic": "false",
        "exclude_from_scoring": "false",
    }]
    with open(filled, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=TEMPLATE_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    # Monkeypatch paths used inside run_stage_r1
    import demand_radar.real_evidence.real_evidence_pipeline as pipeline_mod
    orig_items_path = pipeline_mod._SIGNAL_OUTPUT
    pipeline_mod._SIGNAL_OUTPUT = tmp_path / "signals.csv"

    # Also need to monkeypatch store paths
    import demand_radar.real_evidence.real_evidence_store as store_mod
    orig_items = store_mod._ITEMS_PATH
    orig_val = store_mod._VALIDATION_PATH
    orig_reviews = store_mod._REVIEWS_PATH
    orig_findings = store_mod._FINDINGS_PATH
    store_mod._ITEMS_PATH = tmp_path / "items.jsonl"
    store_mod._VALIDATION_PATH = tmp_path / "val.jsonl"
    store_mod._REVIEWS_PATH = tmp_path / "reviews.jsonl"
    store_mod._FINDINGS_PATH = tmp_path / "findings.jsonl"

    # Monkeypatch report paths
    import demand_radar.real_evidence.calibration_report as cal_mod
    orig_out = cal_mod._OUT
    cal_mod._OUT = tmp_path / "outputs"

    try:
        result = run_stage_r1(template_path=template, filled_path=filled)
        assert result["filled_file_exists"] is True
        assert result["items"] >= 1
    finally:
        pipeline_mod._SIGNAL_OUTPUT = orig_items_path
        store_mod._ITEMS_PATH = orig_items
        store_mod._VALIDATION_PATH = orig_val
        store_mod._REVIEWS_PATH = orig_reviews
        store_mod._FINDINGS_PATH = orig_findings
        cal_mod._OUT = orig_out