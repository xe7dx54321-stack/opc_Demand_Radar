"""Tests for evidence_pack_draft_builder."""
from __future__ import annotations
import csv
from pathlib import Path
from demand_radar.acquisition.acquisition_schema import EvidenceCandidate
from demand_radar.acquisition.evidence_pack_draft_builder import (
    build_evidence_pack_draft,
    DRAFT_COLUMNS,
)


def _candidate(candidate_id="cand_001", status="valid", **kw):
    return EvidenceCandidate(
        candidate_id=candidate_id,
        raw_signal_id="sig_001",
        source_id="hacker_news_ai_investment",
        source_type="community_discussion",
        source_url="https://example.com",
        raw_text="We spend hours manually tracking AI companies with spreadsheets every week.",
        domain_id="ai_investment_tracking",
        domain_title_zh="AI 产业跟踪",
        source_weight=0.90,
        validation_status=status,
        include_in_evidence_pack=(status == "valid"),
        detected_signal_types=["workaround_signal", "time_cost_signal"],
        **kw,
    )


def test_draft_csv_created(tmp_path):
    candidates = [_candidate()]
    out = tmp_path / "draft.csv"
    result = build_evidence_pack_draft(candidates, out)
    assert result.exists()


def test_draft_has_r1_columns(tmp_path):
    candidates = [_candidate()]
    out = tmp_path / "draft.csv"
    build_evidence_pack_draft(candidates, out)
    with open(out, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames or []
    for col in DRAFT_COLUMNS:
        assert col in cols, f"Missing column: {col}"


def test_draft_excludes_invalid(tmp_path):
    candidates = [_candidate("cand_001", "valid"), _candidate("cand_002", "invalid")]
    out = tmp_path / "draft.csv"
    build_evidence_pack_draft(candidates, out, include_only_valid=True)
    with open(out, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["evidence_id"] == "cand_001"


def test_draft_is_synthetic_false(tmp_path):
    candidates = [_candidate()]
    out = tmp_path / "draft.csv"
    build_evidence_pack_draft(candidates, out)
    with open(out, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert rows[0]["is_synthetic"] == "false"


def test_r1_columns_compatible():
    from demand_radar.real_evidence.real_evidence_validator import TEMPLATE_COLUMNS
    for col in DRAFT_COLUMNS:
        assert col in TEMPLATE_COLUMNS, f"Draft column {col} not in R1 template"
