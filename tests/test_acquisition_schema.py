"""Tests for acquisition schema."""
from __future__ import annotations
import pytest
from demand_radar.acquisition.acquisition_schema import EvidenceCandidate, AcquisitionRunSummary


def _base_candidate(**kw):
    defaults = dict(
        candidate_id="cand_001",
        raw_signal_id="sig_001",
        source_id="hacker_news_ai_investment",
        source_type="community_discussion",
        source_url="https://example.com",
        raw_text="We spend hours tracking AI companies manually every week.",
        domain_id="ai_investment_tracking",
        domain_title_zh="AI 产业跟踪",
        source_weight=0.90,
        validation_status="valid",
    )
    defaults.update(kw)
    return defaults


def test_evidence_candidate_valid():
    c = EvidenceCandidate(**_base_candidate())
    assert c.candidate_id == "cand_001"
    assert c.source_weight == 0.90
    assert c.validation_status == "valid"


def test_evidence_candidate_defaults():
    c = EvidenceCandidate(**_base_candidate())
    assert c.include_in_evidence_pack is False
    assert c.validation_reasons == []
    assert c.detected_signal_types == []


def test_acquisition_run_summary_valid():
    s = AcquisitionRunSummary(
        run_id="run_001",
        domain_id="ai_investment_tracking",
        started_at="2026-01-01T00:00:00Z",
        raw_signal_count=50,
        unique_signal_count=40,
        duplicate_count=10,
        evidence_candidate_count=35,
        valid_candidate_count=25,
        warning_candidate_count=5,
        invalid_candidate_count=5,
    )
    assert s.run_id == "run_001"
    assert s.valid_candidate_count == 25


def test_acquisition_run_summary_defaults():
    s = AcquisitionRunSummary(
        run_id="run_002",
        domain_id="ai_investment_tracking",
        started_at="2026-01-01T00:00:00Z",
    )
    assert s.raw_signal_count == 0
    assert s.errors == []
    assert s.by_source == {}
