"""Tests for R1 validation after LLM extraction and LLM pass report."""
import csv
import json
import pytest
from pathlib import Path
from demand_radar.mvp_b.mvp_b_report import build_llm_pass_report, build_r1_validation_comparison_report
from demand_radar.real_evidence.real_evidence_validator import TEMPLATE_COLUMNS


def _make_filled_csv(tmp_path, rows):
    p = tmp_path / "filled.csv"
    with open(p, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=TEMPLATE_COLUMNS)
        writer.writeheader()
        for row in rows:
            full = {col: row.get(col, "") for col in TEMPLATE_COLUMNS}
            writer.writerow(full)
    return p


def _filled_row(eid, has_pain=True):
    row = {
        "evidence_id": eid,
        "target_direction_id": "ai_investment_tracking",
        "source_url": "https://thesisboard.com/",
        "source_type": "community_discussion",
        "raw_text": "I spent 10+ years as an equity portfolio manager. The current solution is spreadsheets.",
        "is_synthetic": "false",
        "exclude_from_scoring": "false" if has_pain else "true",
        "language": "en",
    }
    if has_pain:
        row.update({
            "persona": "equity portfolio manager",
            "workflow_stage": "company_tracking",
            "pain_type": "manual_workflow",
            "evidence_quote": "The current solution is spreadsheets.",
            "evidence_type": "pain_signal",
        })
    return row


# ---- LLM pass report tests ----

def _make_rel(decision="include", score=0.75):
    return {
        "relevance_decision": decision,
        "relevance_score": score,
        "candidate_id": "c001",
        "source_url": "https://example.com",
        "domain_reason_zh": "Test" if decision != "exclude" else None,
        "exclude_reason_zh": "Test" if decision == "exclude" else None,
    }


def _make_pain(strength="medium", should_extract=True):
    return {
        "candidate_id": "c001",
        "should_extract": should_extract,
        "evidence_strength": strength,
        "evidence_quote": "The current solution is spreadsheets." if should_extract else None,
        "persona": "VC analyst" if should_extract else None,
        "workflow_stage": "deal_sourcing" if should_extract else None,
        "pain_type": "manual_workflow" if should_extract else None,
        "pain_description_zh": "Manual work" if should_extract else None,
        "commercial_signal_type": "manual_labor_cost" if should_extract else None,
        "confidence": 0.75 if should_extract else 0.0,
        "reject_reason": None if should_extract else "Not relevant",
        "title": "Test Title",
        "source_url": "https://example.com",
        "metadata": {"cache_hit": False, "quote_matched": True},
    }


def test_llm_pass_report_created(tmp_path):
    rel_dicts = [_make_rel("include", 0.75), _make_rel("uncertain", 0.5)]
    pain_dicts = [_make_pain("medium", True), _make_pain("reject", False)]
    out = tmp_path / "llm_pass.md"
    result = build_llm_pass_report(rel_dicts, pain_dicts, output_path=out)
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "MVP-B LLM Pass Report" in content
    assert "selected_for_llm" in content


def test_llm_pass_report_metadata_fields(tmp_path):
    out = tmp_path / "llm_pass.md"
    build_llm_pass_report(
        [_make_rel()], [_make_pain()],
        provider="anthropic_compatible",
        model="claude-sonnet-4-6",
        real_llm_run=True,
        prompt_version="acquired_signal_pain_extraction_v1",
        output_path=out,
    )
    content = out.read_text(encoding="utf-8")
    assert "anthropic_compatible" in content
    assert "claude-sonnet-4-6" in content
    assert "real_llm_run: True" in content


def test_llm_pass_report_empty_data(tmp_path):
    out = tmp_path / "llm_pass.md"
    build_llm_pass_report([], [], output_path=out)
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "selected_for_llm: 0" in content


def test_r1_comparison_report_created(tmp_path):
    out = tmp_path / "r1_comparison.md"
    r1_before = {"valid": 0, "warning": 10, "invalid": 0}
    r1_after = {"valid": 5, "warning": 5, "invalid": 0}
    result = build_r1_validation_comparison_report(r1_before, r1_after, output_path=out)
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "Before" in content
    assert "After" in content
    assert "Delta" in content


def test_r1_comparison_shows_improvement(tmp_path):
    out = tmp_path / "r1_comp.md"
    build_r1_validation_comparison_report(
        {"valid": 0, "warning": 134, "invalid": 0},
        {"valid": 8, "warning": 126, "invalid": 0},
        output_path=out,
    )
    content = out.read_text(encoding="utf-8")
    assert "+8" in content


def test_r1_validator_can_read_filled_csv(tmp_path):
    """R1 validator runs without error on a properly formed filled CSV."""
    from demand_radar.real_evidence.real_evidence_validator import validate_real_evidence_pack
    filled = _make_filled_csv(tmp_path, [
        _filled_row("e001", has_pain=True),
        _filled_row("e002", has_pain=False),
    ])
    items_out = tmp_path / "items.jsonl"
    vals_out = tmp_path / "vals.jsonl"
    items, vals = validate_real_evidence_pack(filled, items_out, vals_out)
    assert len(items) == 2
    assert len(vals) == 2
    # e001 should at minimum be valid or warning (has raw_text + source_url)
    statuses = {v.evidence_id: v.status for v in vals}
    assert statuses.get("e001") in ("valid", "warning")


def test_gitignore_excludes_llm_cache():
    """Check that .gitignore contains .llm_cache/ entry."""
    gitignore = open(".gitignore", encoding="utf-8").read()
    assert ".llm_cache" in gitignore, ".llm_cache/ not in .gitignore"
