"""Tests for real_evidence_store module."""
from __future__ import annotations
import json
from pathlib import Path
import pytest
from demand_radar.real_evidence.real_evidence_schema import (
    RealEvidenceItem,
    RealEvidenceValidation,
    CalibrationReview,
)
from demand_radar.real_evidence.real_evidence_store import (
    load_real_evidence_items,
    write_real_evidence_items,
    load_real_evidence_validations,
    write_real_evidence_validations,
    load_calibration_reviews,
    write_calibration_reviews,
    append_calibration_review,
    load_calibration_findings,
    write_calibration_findings,
    _ITEMS_PATH,
    _VALIDATION_PATH,
    _REVIEWS_PATH,
    _FINDINGS_PATH,
)
from demand_radar.state.raw_store import utc_now_iso
import demand_radar.real_evidence.real_evidence_store as store_mod


def _patch_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(store_mod, "_ITEMS_PATH", tmp_path / "items.jsonl")
    monkeypatch.setattr(store_mod, "_VALIDATION_PATH", tmp_path / "val.jsonl")
    monkeypatch.setattr(store_mod, "_REVIEWS_PATH", tmp_path / "reviews.jsonl")
    monkeypatch.setattr(store_mod, "_FINDINGS_PATH", tmp_path / "findings.jsonl")


def _item():
    return RealEvidenceItem(
        evidence_id="re_001",
        target_direction_id="ai_investment_tracking",
        target_direction_title_zh="AI 产业跟踪",
        source_url="https://example.com",
        source_type="product_review",
        language="en",
        raw_text="We spend hours tracking AI companies manually every single week.",
        is_synthetic=False,
        exclude_from_scoring=False,
        created_at=utc_now_iso(),
    )


def test_write_and_load_items(tmp_path, monkeypatch):
    _patch_paths(tmp_path, monkeypatch)
    items = [_item()]
    write_real_evidence_items(items)
    loaded = load_real_evidence_items()
    assert len(loaded) == 1
    assert loaded[0].evidence_id == "re_001"


def test_write_and_load_validations(tmp_path, monkeypatch):
    _patch_paths(tmp_path, monkeypatch)
    v = RealEvidenceValidation(
        validation_id="val_001",
        evidence_id="re_001",
        status="valid",
        source_quality="high",
        detected_signal_types=["pain_signal"],
        source_weight=0.95,
        include_in_pipeline=True,
        created_at=utc_now_iso(),
    )
    write_real_evidence_validations([v])
    loaded = load_real_evidence_validations()
    assert len(loaded) == 1
    assert loaded[0].status == "valid"


def test_append_calibration_review(tmp_path, monkeypatch):
    _patch_paths(tmp_path, monkeypatch)
    r = CalibrationReview(
        review_id="cr_001",
        evidence_id="re_001",
        human_labels=["true_pain"],
        created_at=utc_now_iso(),
    )
    append_calibration_review(r)
    append_calibration_review(r)  # append twice
    loaded = load_calibration_reviews()
    assert len(loaded) == 2


def test_write_and_load_reviews(tmp_path, monkeypatch):
    _patch_paths(tmp_path, monkeypatch)
    r = CalibrationReview(
        review_id="cr_001",
        evidence_id="re_001",
        human_labels=["strong_signal", "commercial_signal"],
        created_at=utc_now_iso(),
    )
    write_calibration_reviews([r])
    loaded = load_calibration_reviews()
    assert len(loaded) == 1
    assert "strong_signal" in loaded[0].human_labels


def test_write_and_load_findings(tmp_path, monkeypatch):
    _patch_paths(tmp_path, monkeypatch)
    findings = [{"finding_id": "f_001", "finding_type": "extraction_error", "description_zh": "test"}]
    write_calibration_findings(findings)
    loaded = load_calibration_findings()
    assert len(loaded) == 1
    assert loaded[0]["finding_id"] == "f_001"


def test_load_returns_empty_when_missing(tmp_path, monkeypatch):
    _patch_paths(tmp_path, monkeypatch)
    assert load_real_evidence_items() == []
    assert load_real_evidence_validations() == []
    assert load_calibration_reviews() == []
    assert load_calibration_findings() == []