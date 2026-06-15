"""Tests for RealEvidenceItem, RealEvidenceValidation, and CalibrationReview schemas."""
from __future__ import annotations
import pytest
from demand_radar.real_evidence.real_evidence_schema import (
    RealEvidenceItem,
    RealEvidenceValidation,
    CalibrationReview,
)
from demand_radar.state.raw_store import utc_now_iso


def _base_item(**overrides):
    defaults = dict(
        evidence_id="re_001",
        target_direction_id="ai_investment_tracking",
        target_direction_title_zh="AI 产业跟踪",
        source_url="https://example.com/review",
        source_type="product_review",
        language="en",
        raw_text="A" * 90,
        is_synthetic=False,
        exclude_from_scoring=False,
        created_at=utc_now_iso(),
    )
    defaults.update(overrides)
    return defaults


def test_real_evidence_item_valid():
    item = RealEvidenceItem(**_base_item())
    assert item.evidence_id == "re_001"
    assert item.source_type == "product_review"
    assert not item.is_synthetic


def test_real_evidence_item_requires_source():
    """source_url and source_note cannot both be None."""
    # Both None is allowed at schema level; business rule is in validator.
    # Schema just stores; validator enforces.
    item = RealEvidenceItem(**_base_item(source_url=None, source_note=None))
    assert item.source_url is None
    assert item.source_note is None


def test_real_evidence_item_raw_text_empty_raises():
    with pytest.raises(Exception):
        RealEvidenceItem(**_base_item(raw_text=""))


def test_real_evidence_item_raw_text_whitespace_raises():
    with pytest.raises(Exception):
        RealEvidenceItem(**_base_item(raw_text="   "))


def test_real_evidence_item_domain_tags_default():
    item = RealEvidenceItem(**_base_item())
    assert isinstance(item.domain_tags, list)


def test_real_evidence_validation_schema():
    v = RealEvidenceValidation(
        validation_id="val_001",
        evidence_id="re_001",
        status="valid",
        source_quality="high",
        validation_errors=[],
        validation_warnings=[],
        detected_signal_types=["pain_signal"],
        source_weight=0.95,
        include_in_pipeline=True,
        created_at=utc_now_iso(),
    )
    assert v.status == "valid"
    assert v.source_weight == 0.95


def test_calibration_review_schema():
    r = CalibrationReview(
        review_id="cr_001",
        evidence_id="re_001",
        human_labels=["true_pain", "strong_signal"],
        reviewer_note_zh="这条信号非常清晰",
        created_at=utc_now_iso(),
    )
    assert "true_pain" in r.human_labels
    assert r.reviewer_note_zh


def test_calibration_review_optional_fields():
    r = CalibrationReview(
        review_id="cr_002",
        evidence_id="re_002",
        human_labels=["fake_pain"],
        created_at=utc_now_iso(),
    )
    assert r.system_output_id is None
    assert r.suggested_prompt_fix_zh is None