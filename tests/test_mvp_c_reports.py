"""Tests for MVP-C report builders."""
import pytest
from pathlib import Path
from demand_radar.mvp_c.calibration_report import (
    build_pain_signal_review_report,
    build_calibration_recommendations,
    build_mvp_c_summary_report,
)
from demand_radar.mvp_c.calibration_analyzer import CalibrationFinding
from demand_radar.mvp_c.review_schema import PainSignalReviewSummary
from demand_radar.mvp_c.review_service import PainSignalCard


def _summary(**kw):
    d = dict(total_pain_items=5, reviewed_count=0, unreviewed_count=5)
    d.update(kw)
    return PainSignalReviewSummary(**d)


def _card(pid="p001", reviewed=False):
    rev = None
    if reviewed:
        from demand_radar.mvp_c.review_schema import PainSignalReview
        rev = PainSignalReview(
            review_id=f"rev_{pid}", pain_item_id=pid,
            candidate_id="cand_abc", action_decision="pursue",
            true_pain=True, reviewer_note_zh="Good signal",
            created_at="2026-01-01T00:00:00Z",
        )
    return PainSignalCard(
        pain_item_id=pid, candidate_id="cand_abc",
        title=f"Test Signal {pid}", source_url=f"https://example.com/{pid}",
        source_type="community_discussion", persona="VC analyst",
        workflow_stage="deal_sourcing", pain_type="manual_workflow",
        pain_description_zh="Test pain", evidence_quote="We spend hours on this.",
        current_solution="spreadsheets", commercial_signal_type="manual_labor_cost",
        evidence_strength="strong", confidence=0.85,
        reasoning_summary_zh="Strong investment signal",
        existing_review=rev,
    )


def test_review_report_created(tmp_path):
    out = tmp_path / "review_report.md"
    build_pain_signal_review_report([], _summary(), output_path=out)
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "MVP-C Pain Signal Review Report" in content


def test_review_report_with_reviewed_items(tmp_path):
    out = tmp_path / "review_report.md"
    cards = [_card("p001", reviewed=True), _card("p002", reviewed=False)]
    build_pain_signal_review_report(cards, _summary(reviewed_count=1, unreviewed_count=1), output_path=out)
    content = out.read_text(encoding="utf-8")
    assert "Reviewed Pain Signals" in content


def test_calibration_recommendations_created(tmp_path):
    out = tmp_path / "calibration.md"
    findings = [
        CalibrationFinding(
            finding_id="f001", finding_type="prompt_issue",
            severity="high", description_zh="Test",
            recommended_fix_zh="Fix prompt", affected_items=["p001"],
        )
    ]
    build_calibration_recommendations(findings, output_path=out)
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "Calibration Recommendations" in content
    assert "Prompt Issues" in content


def test_calibration_recommendations_empty_findings(tmp_path):
    out = tmp_path / "calibration.md"
    build_calibration_recommendations([], output_path=out)
    assert out.exists()


def test_mvp_c_summary_report_no_reviews(tmp_path):
    out = tmp_path / "summary.md"
    build_mvp_c_summary_report(_summary(), [], output_path=out)
    content = out.read_text(encoding="utf-8")
    assert "MVP-C Summary Report" in content
    assert "FAIL" in content or "PARTIAL" in content


def test_mvp_c_summary_report_with_reviews(tmp_path):
    out = tmp_path / "summary.md"
    s = _summary(
        reviewed_count=4, unreviewed_count=1,
        true_pain_count=3, pursue_count=3, watch_count=1,
    )
    build_mvp_c_summary_report(s, [], output_path=out)
    content = out.read_text(encoding="utf-8")
    assert "PASS" in content
