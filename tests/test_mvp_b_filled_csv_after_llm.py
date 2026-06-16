"""Tests for filled CSV after LLM extraction."""
import csv
import json
import pytest
from pathlib import Path
from demand_radar.mvp_b.evidence_pack_filler import fill_evidence_pack
from demand_radar.real_evidence.real_evidence_validator import TEMPLATE_COLUMNS


def _make_draft(tmp_path, rows):
    p = tmp_path / "draft.csv"
    with open(p, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=TEMPLATE_COLUMNS)
        writer.writeheader()
        for row in rows:
            full = {col: row.get(col, "") for col in TEMPLATE_COLUMNS}
            writer.writerow(full)
    return p


def _base_row(eid, **kw):
    row = {
        "evidence_id": eid,
        "target_direction_id": "ai_investment_tracking",
        "source_url": "https://thesisboard.com/",
        "source_type": "community_discussion",
        "raw_text": "I spent 10+ years as an equity portfolio manager. The current solution is spreadsheets.",
        "is_synthetic": "false",
        "exclude_from_scoring": "false",
    }
    row.update(kw)
    return row


def _good_pain(cid):
    return {
        "candidate_id": cid,
        "should_extract": True,
        "evidence_strength": "strong",
        "evidence_quote": "The current solution is spreadsheets.",
        "persona": "equity portfolio manager",
        "persona_confidence": 0.9,
        "workflow_stage": "company_tracking",
        "pain_type": "manual_workflow",
        "pain_description_zh": "手动追踪研究信息",
        "current_solution": "spreadsheets",
        "paid_alternative": None,
        "business_impact": "hours wasted",
        "time_cost_signal": "hours",
        "budget_signal": None,
        "commercial_signal_type": "manual_labor_cost",
        "reject_reason": None,
    }


def _good_rel(cid):
    return {
        "candidate_id": cid,
        "relevance_decision": "include",
        "relevance_score": 0.75,
        "domain_reason_zh": "Investment research signal",
    }


def test_llm_extracted_fields_filled(tmp_path):
    draft = _make_draft(tmp_path, [_base_row("e001")])
    out = tmp_path / "filled.csv"
    fill_evidence_pack(
        draft_path=draft,
        relevance_dicts=[_good_rel("e001")],
        pain_dicts=[_good_pain("e001")],
        output_path=out,
    )
    with open(out, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    row = rows[0]
    assert row["persona"] == "equity portfolio manager"
    assert row["workflow_stage"] == "company_tracking"
    assert row["pain_type"] == "manual_workflow"
    assert row["evidence_quote"] == "The current solution is spreadsheets."
    assert row["commercial_signal_type"] == "manual_labor_cost"
    assert row["exclude_from_scoring"] == "false"


def test_all_template_columns_present(tmp_path):
    draft = _make_draft(tmp_path, [_base_row("e002")])
    out = tmp_path / "filled.csv"
    fill_evidence_pack(
        draft_path=draft,
        relevance_dicts=[_good_rel("e002")],
        pain_dicts=[_good_pain("e002")],
        output_path=out,
    )
    with open(out, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    for col in TEMPLATE_COLUMNS:
        assert col in rows[0], f"Missing column: {col}"


def test_exclude_when_relevance_exclude(tmp_path):
    draft = _make_draft(tmp_path, [_base_row("e003")])
    out = tmp_path / "filled.csv"
    fill_evidence_pack(
        draft_path=draft,
        relevance_dicts=[{
            "candidate_id": "e003",
            "relevance_decision": "exclude",
            "relevance_score": 0.05,
            "exclude_reason_zh": "Off domain",
        }],
        pain_dicts=[],
        output_path=out,
    )
    with open(out, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["exclude_from_scoring"] == "true"


def test_exclude_when_pain_reject(tmp_path):
    draft = _make_draft(tmp_path, [_base_row("e004")])
    out = tmp_path / "filled.csv"
    reject_pain = {
        "candidate_id": "e004",
        "should_extract": False,
        "evidence_strength": "reject",
        "reject_reason": "LLM extraction failed",
    }
    fill_evidence_pack(
        draft_path=draft,
        relevance_dicts=[_good_rel("e004")],
        pain_dicts=[reject_pain],
        output_path=out,
    )
    with open(out, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["exclude_from_scoring"] == "true"


def test_collector_note_written(tmp_path):
    draft = _make_draft(tmp_path, [_base_row("e005")])
    out = tmp_path / "filled.csv"
    fill_evidence_pack(
        draft_path=draft,
        relevance_dicts=[_good_rel("e005")],
        pain_dicts=[_good_pain("e005")],
        output_path=out,
    )
    with open(out, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert "mvp_b_extracted" in rows[0].get("collector_note", "")


def test_multiple_rows_mixed(tmp_path):
    rows_in = [
        _base_row("e010"),  # good
        _base_row("e011"),  # excluded by domain
        _base_row("e012"),  # rejected by pain
    ]
    draft = _make_draft(tmp_path, rows_in)
    out = tmp_path / "filled.csv"
    fill_evidence_pack(
        draft_path=draft,
        relevance_dicts=[
            _good_rel("e010"),
            {"candidate_id": "e011", "relevance_decision": "exclude", "relevance_score": 0.05, "exclude_reason_zh": "off domain"},
            _good_rel("e012"),
        ],
        pain_dicts=[
            _good_pain("e010"),
            {"candidate_id": "e012", "should_extract": False, "evidence_strength": "reject", "reject_reason": "No pain"},
        ],
        output_path=out,
    )
    with open(out, encoding="utf-8") as f:
        result = list(csv.DictReader(f))
    assert result[0]["exclude_from_scoring"] == "false"
    assert result[1]["exclude_from_scoring"] == "true"
    assert result[2]["exclude_from_scoring"] == "true"
