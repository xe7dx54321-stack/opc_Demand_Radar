"""Tests for acquisition report generation."""
from __future__ import annotations
from pathlib import Path
from demand_radar.acquisition.acquisition_schema import EvidenceCandidate, AcquisitionRunSummary
from demand_radar.acquisition.acquisition_report import (
    build_acquisition_report,
    build_evidence_pack_draft_report,
)
from opc_foundation.run.time_utils import utcnow_iso


def _summary(**kw):
    defaults = dict(
        run_id="run_001",
        domain_id="ai_investment_tracking",
        started_at=utcnow_iso(),
        raw_signal_count=10,
        unique_signal_count=8,
        duplicate_count=2,
        evidence_candidate_count=7,
        valid_candidate_count=5,
        warning_candidate_count=1,
        invalid_candidate_count=1,
    )
    defaults.update(kw)
    return AcquisitionRunSummary(**defaults)


def _candidate():
    return EvidenceCandidate(
        candidate_id="cand_001",
        raw_signal_id="sig_001",
        source_id="hacker_news_ai_investment",
        source_type="community_discussion",
        source_url="https://example.com",
        raw_text="AI tracking manually hours every week spreadsheet tedious workflow.",
        domain_id="ai_investment_tracking",
        domain_title_zh="AI 产业跟踪",
        source_weight=0.90,
        validation_status="valid",
        include_in_evidence_pack=True,
        detected_signal_types=["workflow_signal", "time_cost_signal"],
    )


def test_build_acquisition_report(tmp_path):
    s = _summary()
    out = tmp_path / "report.md"
    result = build_acquisition_report(s, [_candidate()], out)
    assert result.exists()
    content = result.read_text(encoding="utf-8")
    assert "Acquisition Report" in content
    assert "run_001" in content


def test_acquisition_report_includes_errors(tmp_path):
    s = _summary(errors=["HN fetch error: timeout"])
    out = tmp_path / "report.md"
    result = build_acquisition_report(s, [], out)
    content = result.read_text(encoding="utf-8")
    assert "timeout" in content


def test_build_draft_report(tmp_path):
    draft = tmp_path / "draft.csv"
    draft.write_bytes(b"evidence_id\n")
    out = tmp_path / "draft_report.md"
    result = build_evidence_pack_draft_report([_candidate()], draft, out)
    assert result.exists()
    content = result.read_text(encoding="utf-8")
    assert "Draft" in content
