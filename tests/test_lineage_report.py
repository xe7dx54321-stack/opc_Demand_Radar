"""Tests for Stage 3.4 lineage report generation."""
import pytest
from datetime import datetime, timezone
from pathlib import Path
from demand_radar.lineage.lineage_schema import (
    CandidateLineage, TargetedEvidenceAttribution, StableTruthScoreDelta
)
from demand_radar.lineage.lineage_report import (
    build_candidate_lineage_report,
    build_targeted_evidence_attribution_report,
    build_stable_truth_score_delta_report,
)

NOW = datetime.now(timezone.utc).isoformat()


def _lineage(lid, strength="weak", b_title="before", a_title="after",
             b_score=60.0, a_score=68.0, drift=None):
    return CandidateLineage(
        lineage_id=lid,
        match_strength=strength,
        match_score=0.6,
        before_group_id="grp_b",
        before_group_title_zh=b_title,
        before_truth_score=b_score,
        before_truth_level="medium",
        after_group_id="grp_a",
        after_group_title_zh=a_title,
        after_truth_score=a_score,
        after_truth_level="medium",
        drift_flags=drift or [],
        lineage_summary_zh="test summary",
        created_at=NOW,
    )


def _attr(aid, status="attributed_to_expected_group", intent="paid_alternative"):
    return TargetedEvidenceAttribution(
        attribution_id=aid,
        target_signal_id=f"tsig_{aid}",
        target_group_id="grp_b",
        attribution_status=status,
        attribution_confidence=0.8,
        attribution_reason_zh="test",
        evidence_intent=intent,
        reviewed_group_ids=["grp_a"],
        created_at=NOW,
    )


def _delta(did, confidence="medium", action="keep_watch", delta=8.0):
    return StableTruthScoreDelta(
        stable_delta_id=did,
        lineage_id="l1",
        before_group_title_zh="before",
        after_group_title_zh="after",
        before_truth_score=60.0,
        after_truth_score=68.0,
        stable_delta=delta,
        before_truth_level="medium",
        after_truth_level="medium",
        delta_confidence=confidence,
        interpretation_zh="test interpretation",
        recommended_next_action=action,
        created_at=NOW,
    )


def test_lineage_report_created_empty(tmp_path):
    out = tmp_path / "lineage_report.md"
    build_candidate_lineage_report([], output_path=str(out))
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "Candidate Lineage Report" in content


def test_lineage_report_contains_summary_counts(tmp_path):
    lineages = [_lineage("l1", "strong"), _lineage("l2", "weak"), _lineage("l3", "unmatched")]
    out = tmp_path / "lineage_report.md"
    build_candidate_lineage_report(lineages, output_path=str(out))
    content = out.read_text(encoding="utf-8")
    assert "strong" in content.lower() or "Strong" in content
    assert "weak" in content.lower() or "Weak" in content


def test_lineage_report_shows_drift_flags(tmp_path):
    lineages = [_lineage("l1", "weak", drift=["group_title_drift"])]
    out = tmp_path / "lineage_report.md"
    build_candidate_lineage_report(lineages, output_path=str(out))
    content = out.read_text(encoding="utf-8")
    assert "group_title_drift" in content


def test_attribution_report_created_empty(tmp_path):
    out = tmp_path / "attr_report.md"
    build_targeted_evidence_attribution_report([], output_path=str(out))
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "Attribution" in content


def test_attribution_report_shows_statuses(tmp_path):
    attrs = [
        _attr("a1", "attributed_to_expected_group"),
        _attr("a2", "lost_in_extraction"),
        _attr("a3", "not_used"),
    ]
    out = tmp_path / "attr_report.md"
    build_targeted_evidence_attribution_report(attrs, output_path=str(out))
    content = out.read_text(encoding="utf-8")
    assert "attributed" in content.lower() or "Attribution" in content
    assert "lost" in content.lower() or "3" in content


def test_attribution_report_shows_rate(tmp_path):
    attrs = [
        _attr("a1", "attributed_to_expected_group"),
        _attr("a2", "attributed_to_expected_group"),
        _attr("a3", "lost_in_extraction"),
        _attr("a4", "lost_in_merge"),
    ]
    out = tmp_path / "attr_report.md"
    build_targeted_evidence_attribution_report(attrs, output_path=str(out))
    content = out.read_text(encoding="utf-8")
    assert "%" in content or "rate" in content.lower() or "50" in content


def test_stable_delta_report_created_empty(tmp_path):
    out = tmp_path / "delta_report.md"
    build_stable_truth_score_delta_report([], output_path=str(out))
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "Delta" in content


def test_stable_delta_report_shows_confidence(tmp_path):
    deltas = [_delta("d1", "high"), _delta("d2", "medium"), _delta("d3", "low")]
    out = tmp_path / "delta_report.md"
    build_stable_truth_score_delta_report(deltas, output_path=str(out))
    content = out.read_text(encoding="utf-8")
    assert "high" in content.lower() or "High" in content
    assert "medium" in content.lower() or "Medium" in content


def test_stable_delta_report_shows_recommended_action(tmp_path):
    deltas = [_delta("d1", "high", action="proceed_to_fit_scoring")]
    out = tmp_path / "delta_report.md"
    build_stable_truth_score_delta_report(deltas, output_path=str(out))
    content = out.read_text(encoding="utf-8")
    assert "proceed_to_fit_scoring" in content or "Fit Scoring" in content
