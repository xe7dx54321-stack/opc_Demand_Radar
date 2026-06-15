"""Tests for Stage 3.3 expansion_report."""
import pytest
from pathlib import Path
from datetime import datetime, timezone
from demand_radar.targeted_expansion.expansion_report import (
    build_targeted_expansion_report,
    build_truth_score_delta_report,
)
from demand_radar.targeted_expansion.targeted_schema import (
    TargetedExpansionSummary,
    TargetedSignalValidation,
    TruthScoreDelta,
)


def _now():
    return datetime.now(timezone.utc).isoformat()


def _make_summary(**kwargs):
    defaults = dict(
        template_rows=40,
        filled_signals=35,
        valid_signals=30,
        warning_signals=3,
        invalid_signals=2,
        excluded_synthetic=0,
        combined_input_rows=110,
        base_rows=80,
        targeted_rows_included=30,
        duplicates_removed=0,
        created_at=_now(),
    )
    defaults.update(kwargs)
    return TargetedExpansionSummary(**defaults)


def _make_validation(sig_id, status, intent=None, errors=None, warnings=None):
    return TargetedSignalValidation(
        validation_id=f"val_{sig_id}",
        target_signal_id=sig_id,
        status=status,
        evidence_intent=intent,
        validation_errors=errors or [],
        validation_warnings=warnings or [],
        include_in_combined_input=(status == "valid"),
        created_at=_now(),
    )


def _make_delta(group_id, title, before, after, before_level="medium", after_level="medium",
                before_action="needs_more_evidence", after_action="needs_more_evidence",
                improved=None, gaps=None):
    delta = after - before if before is not None and after is not None else None
    return TruthScoreDelta(
        source_group_id=group_id,
        group_title_zh=title,
        before_truth_score=before,
        after_truth_score=after,
        delta=delta,
        before_truth_level=before_level,
        after_truth_level=after_level,
        before_next_action=before_action,
        after_next_action=after_action,
        improved_dimensions=improved or [],
        remaining_gaps=gaps or [],
        created_at=_now(),
    )


def test_targeted_expansion_report_no_data(tmp_path):
    out = tmp_path / "report.md"
    build_targeted_expansion_report(None, [], output_path=str(out))
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "Targeted Evidence Expansion Report" in content


def test_targeted_expansion_report_with_summary(tmp_path):
    summary = _make_summary()
    validations = [
        _make_validation("tsig_001", "valid", intent="paid_alternative"),
        _make_validation("tsig_002", "warning", intent="budget_signal",
                        warnings=["no payment keywords"]),
        _make_validation("tsig_003", "invalid", errors=["collected but raw_text empty"]),
    ]
    out = tmp_path / "report.md"
    build_targeted_expansion_report(summary, validations, output_path=str(out))
    content = out.read_text(encoding="utf-8")
    assert "Template rows: 40" in content
    assert "valid" in content
    assert "invalid" in content


def test_truth_score_delta_report_empty(tmp_path):
    out = tmp_path / "delta.md"
    build_truth_score_delta_report([], output_path=str(out))
    content = out.read_text(encoding="utf-8")
    assert "No comparison available" in content


def test_truth_score_delta_report_with_improvement(tmp_path):
    deltas = [
        _make_delta("grp_001", "内容团队选题准备", before=66.4, after=78.0,
                    after_level="strong", after_action="proceed_to_fit_scoring",
                    improved=["willingness_to_pay", "existing_workaround"]),
        _make_delta("grp_002", "投资人AI产业跟踪", before=60.4, after=63.0),
    ]
    out = tmp_path / "delta.md"
    build_truth_score_delta_report(deltas, output_path=str(out))
    content = out.read_text(encoding="utf-8")
    assert "Compared candidates: 2" in content
    assert "Improved: 2" in content
    assert "New strong candidates: 1" in content
    assert "内容团队选题准备" in content


def test_truth_score_delta_report_no_change(tmp_path):
    deltas = [
        _make_delta("grp_001", "测试候选", before=60.0, after=60.0),
    ]
    out = tmp_path / "delta.md"
    build_truth_score_delta_report(deltas, output_path=str(out))
    content = out.read_text(encoding="utf-8")
    assert "Unchanged: 1" in content
