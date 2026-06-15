"""Tests for calibrated_llm readiness (Stage 2.9C)."""
from __future__ import annotations

from demand_radar.semantic_merge.calibration_report import build_llm_calibration_report, CalibrationReportSummary


def test_calibration_summary_model():
    summary = CalibrationReportSummary(
        merge_candidates=102,
        prev_auto_confirmed=5,
        cal_auto_confirmed=15,
        prev_auto_rejected=0,
        cal_auto_rejected=12,
        prev_human_exceptions=97,
        cal_human_exceptions=75,
        prev_exception_rate=0.951,
        cal_exception_rate=0.735,
        prev_ai_groups=3,
        cal_ai_groups=8,
        preflight_ok=97,
        preflight_repaired=3,
        preflight_invalid=2,
        rejects_unlocked=12,
        confirms_unlocked=10,
    )
    assert summary.cal_ai_groups == 8
    assert summary.cal_exception_rate == 0.735
    assert summary.rejects_unlocked == 12
    assert summary.confirms_unlocked == 10


def test_calibration_report_enter_stage3(tmp_path):
    """Report recommendation should say yes if groups>=5 and rate<=0.45."""
    from pathlib import Path
    out = tmp_path / "r.md"
    build_llm_calibration_report(
        prev_judgments_path=Path("nonexistent.jsonl"),
        cal_judgments_path=Path("nonexistent.jsonl"),
        prev_groups_path=Path("nonexistent.jsonl"),
        cal_groups_path=Path("nonexistent.jsonl"),
        preflight_path=Path("nonexistent.jsonl"),
        output_path=out,
    )
    content = out.read_text(encoding="utf-8")
    # With 0 groups: recommendation should be "no"
    assert "Enter Stage 3" in content