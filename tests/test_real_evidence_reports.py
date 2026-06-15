"""Tests for calibration_report module."""
from __future__ import annotations
from pathlib import Path
from demand_radar.real_evidence.real_evidence_schema import (
    RealEvidenceItem,
    RealEvidenceValidation,
    CalibrationReview,
)
from demand_radar.real_evidence.calibration_report import (
    build_real_evidence_pack_report,
    build_calibration_report,
    build_prompt_skill_recommendations,
)
from demand_radar.state.raw_store import utc_now_iso


def _item(evidence_id="re_001", source_type="product_review"):
    return RealEvidenceItem(
        evidence_id=evidence_id,
        target_direction_id="ai_investment_tracking",
        target_direction_title_zh="AI 产业跟踪",
        source_url="https://example.com",
        source_type=source_type,
        language="en",
        raw_text="We spend hours every week manually tracking AI companies. Very painful and costly.",
        is_synthetic=False,
        exclude_from_scoring=False,
        created_at=utc_now_iso(),
    )


def _validation(evidence_id="re_001", status="valid"):
    return RealEvidenceValidation(
        validation_id="val_001",
        evidence_id=evidence_id,
        status=status,
        source_quality="high",
        detected_signal_types=["pain_signal"],
        source_weight=0.95,
        include_in_pipeline=True,
        created_at=utc_now_iso(),
    )


def _review(evidence_id="re_001"):
    return CalibrationReview(
        review_id="cr_001",
        evidence_id=evidence_id,
        human_labels=["true_pain", "strong_signal"],
        reviewer_note_zh="很好的信号",
        suggested_prompt_fix_zh="需要更好的角色识别",
        created_at=utc_now_iso(),
    )


def test_build_evidence_pack_report(tmp_path):
    items = [_item()]
    validations = [_validation()]
    out = tmp_path / "pack_report.md"
    result = build_real_evidence_pack_report(items, validations, out)
    assert result.exists()
    content = result.read_text(encoding="utf-8")
    assert "Real Evidence Pack Report" in content
    assert "Evidence items" in content


def test_build_calibration_report_empty(tmp_path):
    out = tmp_path / "cal_report.md"
    result = build_calibration_report([], out)
    assert result.exists()
    content = result.read_text(encoding="utf-8")
    assert "Calibration Report" in content
    assert "No calibration reviews" in content


def test_build_calibration_report_with_reviews(tmp_path):
    reviews = [_review()]
    out = tmp_path / "cal_report.md"
    result = build_calibration_report(reviews, out)
    content = result.read_text(encoding="utf-8")
    assert "True pain: 1" in content


def test_build_prompt_skill_recommendations(tmp_path):
    reviews = [_review()]
    out = tmp_path / "recs.md"
    result = build_prompt_skill_recommendations(reviews, [], out)
    assert result.exists()
    content = result.read_text(encoding="utf-8")
    assert "Calibration Recommendations" in content
    assert "Extraction Prompt Fixes" in content


def test_build_reports_with_no_items(tmp_path):
    out = tmp_path / "empty_pack.md"
    result = build_real_evidence_pack_report([], [], out)
    content = result.read_text(encoding="utf-8")
    assert "Evidence items: 0" in content