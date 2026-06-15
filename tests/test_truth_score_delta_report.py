"""Tests for truth score delta report - delta logic focus."""
import pytest
from pathlib import Path
from datetime import datetime, timezone
from demand_radar.targeted_expansion.expansion_report import build_truth_score_delta_report
from demand_radar.targeted_expansion.targeted_schema import TruthScoreDelta


def _now():
    return datetime.now(timezone.utc).isoformat()


def _delta(grp, title, before, after, b_level="medium", a_level="medium",
           b_action="needs_more_evidence", a_action="needs_more_evidence",
           improved=None, gaps=None):
    d = after - before if before is not None and after is not None else None
    return TruthScoreDelta(
        source_group_id=grp,
        group_title_zh=title,
        before_truth_score=before,
        after_truth_score=after,
        delta=d,
        before_truth_level=b_level,
        after_truth_level=a_level,
        before_next_action=b_action,
        after_next_action=a_action,
        improved_dimensions=improved or [],
        remaining_gaps=gaps or [],
        created_at=_now(),
    )


def test_decline_counted(tmp_path):
    deltas = [
        _delta("g1", "候选1", before=70.0, after=65.0),
    ]
    out = tmp_path / "delta.md"
    build_truth_score_delta_report(deltas, output_path=str(out))
    content = out.read_text(encoding="utf-8")
    assert "Declined: 1" in content


def test_multiple_candidates_sorted_by_delta(tmp_path):
    deltas = [
        _delta("g1", "候选A", before=60.0, after=78.0, a_level="strong",
               a_action="proceed_to_fit_scoring"),
        _delta("g2", "候选B", before=58.0, after=63.0),
    ]
    out = tmp_path / "delta.md"
    build_truth_score_delta_report(deltas, output_path=str(out))
    content = out.read_text(encoding="utf-8")
    # 候选A (delta=18) should appear before 候选B (delta=5)
    idx_a = content.find("候选A")
    idx_b = content.find("候选B")
    assert idx_a < idx_b


def test_new_proceed_to_fit_scoring_counted(tmp_path):
    deltas = [
        _delta("g1", "强需求候选", before=72.0, after=80.0,
               a_level="strong", a_action="proceed_to_fit_scoring"),
    ]
    out = tmp_path / "delta.md"
    build_truth_score_delta_report(deltas, output_path=str(out))
    content = out.read_text(encoding="utf-8")
    assert "New proceed_to_fit_scoring: 1" in content


def test_delta_report_shows_improved_dimensions(tmp_path):
    deltas = [
        _delta("g1", "测试候选", before=60.0, after=70.0,
               improved=["willingness_to_pay", "existing_workaround"]),
    ]
    out = tmp_path / "delta.md"
    build_truth_score_delta_report(deltas, output_path=str(out))
    content = out.read_text(encoding="utf-8")
    assert "willingness_to_pay" in content


def test_delta_report_shows_remaining_gaps(tmp_path):
    deltas = [
        _delta("g1", "有缺口候选", before=58.0, after=65.0,
               gaps=["frequency_repetition", "persona_clarity"]),
    ]
    out = tmp_path / "delta.md"
    build_truth_score_delta_report(deltas, output_path=str(out))
    content = out.read_text(encoding="utf-8")
    assert "frequency_repetition" in content
