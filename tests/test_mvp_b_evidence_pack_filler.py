"""Tests for evidence pack filler."""
import csv
import pytest
from pathlib import Path
from demand_radar.mvp_b.evidence_pack_filler import fill_evidence_pack
from demand_radar.real_evidence.real_evidence_validator import TEMPLATE_COLUMNS


def _make_draft_csv(tmp_path, rows):
    p = tmp_path / "draft.csv"
    with open(p, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=TEMPLATE_COLUMNS)
        writer.writeheader()
        for row in rows:
            complete = {col: row.get(col, "") for col in TEMPLATE_COLUMNS}
            writer.writerow(complete)
    return p


def _base_row(evidence_id, **kw):
    row = {
        "evidence_id": evidence_id,
        "target_direction_id": "ai_investment_tracking",
        "source_url": "https://example.com/test",
        "source_type": "community_discussion",
        "raw_text": "We spend hours manually tracking startups in spreadsheets for deal sourcing.",
        "is_synthetic": "false",
        "exclude_from_scoring": "false",
    }
    row.update(kw)
    return row


def test_output_has_all_template_columns(tmp_path):
    draft = _make_draft_csv(tmp_path, [_base_row("e001")])
    out = tmp_path / "filled.csv"
    fill_evidence_pack(draft_path=draft, output_path=out)
    with open(out, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) == 1
    for col in TEMPLATE_COLUMNS:
        assert col in rows[0], f"Missing column: {col}"


def test_pain_fields_filled_when_extract_true(tmp_path):
    draft = _make_draft_csv(tmp_path, [_base_row("e001")])
    out = tmp_path / "filled.csv"
    rel_dicts = [{
        "candidate_id": "e001",
        "relevance_decision": "include",
        "relevance_score": 0.80,
        "domain_reason_zh": "Investment research signal",
    }]
    pain_dicts = [{
        "candidate_id": "e001",
        "should_extract": True,
        "evidence_strength": "medium",
        "evidence_quote": "We spend hours manually tracking startups.",
        "persona": "VC analyst",
        "persona_confidence": 0.85,
        "workflow_stage": "deal_sourcing",
        "pain_type": "information_scattered",
        "pain_description_zh": "Manual tracking is painful",
        "current_solution": "spreadsheets",
        "commercial_signal_type": "manual_labor_cost",
    }]
    fill_evidence_pack(draft_path=draft, relevance_dicts=rel_dicts, pain_dicts=pain_dicts, output_path=out)
    with open(out, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    row = rows[0]
    assert row["persona"] == "VC analyst"
    assert row["workflow_stage"] == "deal_sourcing"
    assert row["evidence_quote"] == "We spend hours manually tracking startups."
    assert row["exclude_from_scoring"] == "false"


def test_exclude_when_relevance_exclude(tmp_path):
    draft = _make_draft_csv(tmp_path, [_base_row("e002")])
    out = tmp_path / "filled.csv"
    rel_dicts = [{
        "candidate_id": "e002",
        "relevance_decision": "exclude",
        "relevance_score": 0.10,
        "exclude_reason_zh": "Not investment domain",
    }]
    pain_dicts = []
    fill_evidence_pack(draft_path=draft, relevance_dicts=rel_dicts, pain_dicts=pain_dicts, output_path=out)
    with open(out, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["exclude_from_scoring"] == "true"


def test_exclude_when_should_extract_false(tmp_path):
    draft = _make_draft_csv(tmp_path, [_base_row("e003")])
    out = tmp_path / "filled.csv"
    rel_dicts = [{"candidate_id": "e003", "relevance_decision": "include", "relevance_score": 0.75, "domain_reason_zh": "OK"}]
    pain_dicts = [{"candidate_id": "e003", "should_extract": False, "evidence_strength": "reject", "reject_reason": "test"}]
    fill_evidence_pack(draft_path=draft, relevance_dicts=rel_dicts, pain_dicts=pain_dicts, output_path=out)
    with open(out, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["exclude_from_scoring"] == "true"


def test_synthetic_always_excluded(tmp_path):
    draft = _make_draft_csv(tmp_path, [_base_row("e004", is_synthetic="true")])
    out = tmp_path / "filled.csv"
    fill_evidence_pack(draft_path=draft, output_path=out)
    with open(out, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["exclude_from_scoring"] == "true"


def test_missing_draft_creates_empty_output(tmp_path):
    out = tmp_path / "filled.csv"
    result = fill_evidence_pack(draft_path=tmp_path / "nonexistent.csv", output_path=out)
    assert out.exists()
    with open(out, encoding="utf-8") as f:
        content = f.read()
    assert TEMPLATE_COLUMNS[0] in content


def test_multiple_rows(tmp_path):
    rows = [_base_row(f"e{i:03d}") for i in range(5)]
    draft = _make_draft_csv(tmp_path, rows)
    out = tmp_path / "filled.csv"
    fill_evidence_pack(draft_path=draft, output_path=out)
    with open(out, encoding="utf-8") as f:
        result_rows = list(csv.DictReader(f))
    assert len(result_rows) == 5
