"""Tests for calibration report (Stage 2.9C)."""
from __future__ import annotations

from pathlib import Path

import pytest

from demand_radar.semantic_merge.calibration_report import build_llm_calibration_report
from demand_radar.semantic_merge.calibration_runner import (
    CALIBRATED_GROUPS_PATH,
    CALIBRATED_JUDGMENTS_PATH,
)


def test_build_calibration_report_no_data(tmp_path):
    """Report can be built even when input files do not exist."""
    out = tmp_path / "report.md"
    summary = build_llm_calibration_report(
        prev_judgments_path=Path("nonexistent_prev.jsonl"),
        cal_judgments_path=Path("nonexistent_cal.jsonl"),
        prev_groups_path=Path("nonexistent_prev_groups.jsonl"),
        cal_groups_path=Path("nonexistent_cal_groups.jsonl"),
        preflight_path=Path("nonexistent_preflight.jsonl"),
        output_path=out,
    )
    assert out.exists()
    assert summary.merge_candidates == 0
    assert summary.prev_auto_confirmed == 0
    assert summary.cal_auto_confirmed == 0


@pytest.mark.slow
def test_build_calibration_report_with_existing(tmp_path):
    """If calibrated judgments exist, report should include them."""
    if not CALIBRATED_JUDGMENTS_PATH.exists():
        pytest.skip("Calibrated judgments not generated yet")
    out = tmp_path / "cal_report.md"
    summary = build_llm_calibration_report(output_path=out)
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "Calibration Report" in content
    assert "Recommendation" in content
    assert summary.merge_candidates > 0