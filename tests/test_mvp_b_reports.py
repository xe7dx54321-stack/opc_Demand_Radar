"""Tests for MVP-B report builders."""
import pytest
from pathlib import Path
from demand_radar.mvp_b.mvp_b_report import (
    build_domain_relevance_report,
    build_pain_extraction_report,
    build_top_pain_signals_report,
    build_mvp_b_summary_report,
)


def _rel(decision, score=0.5, url="https://example.com"):
    return {
        "relevance_decision": decision,
        "relevance_score": score,
        "source_url": url,
        "domain_reason_zh": "Test reason" if decision != "exclude" else None,
        "exclude_reason_zh": "Excluded reason" if decision == "exclude" else None,
    }


def _pain(strength, should_extract=True, pain_type="manual_workflow", workflow="deal_sourcing"):
    return {
        "should_extract": should_extract,
        "evidence_strength": strength,
        "pain_type": pain_type,
        "workflow_stage": workflow,
        "persona": "VC analyst",
        "pain_description_zh": "Manual tracking is painful",
        "evidence_quote": "We spend hours on this.",
        "commercial_signal_type": "manual_labor_cost",
        "confidence": 0.75,
        "source_url": "https://example.com",
        "title": "Test Title",
    }


def test_domain_relevance_report_created(tmp_path):
    rel_dicts = [_rel("include", 0.8), _rel("exclude", 0.1), _rel("uncertain", 0.5)]
    out = tmp_path / "domain_rel.md"
    result = build_domain_relevance_report(rel_dicts, output_path=out)
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "Domain Relevance Report" in content
    assert "Include: 1" in content
    assert "Exclude: 1" in content


def test_pain_extraction_report_created(tmp_path):
    pain_dicts = [_pain("strong"), _pain("medium"), _pain("reject", should_extract=False)]
    out = tmp_path / "pain.md"
    result = build_pain_extraction_report(pain_dicts, output_path=out)
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "Pain Extraction Report" in content


def test_top_pain_signals_report_created(tmp_path):
    pain_dicts = [_pain("strong"), _pain("medium")]
    out = tmp_path / "top.md"
    result = build_top_pain_signals_report(pain_dicts, output_path=out)
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "Pain Signals" in content


def test_mvp_b_summary_report_created(tmp_path):
    rel_dicts = [_rel("include"), _rel("exclude")]
    pain_dicts = [_pain("strong")]
    out = tmp_path / "summary.md"
    r1_before = {"valid": 10, "warning": 5, "invalid": 2}
    r1_after = {"valid": 12, "warning": 3, "invalid": 2}
    result = build_mvp_b_summary_report(rel_dicts, pain_dicts, r1_before, r1_after, output_path=out)
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "MVP-B" in content


def test_reports_empty_data(tmp_path):
    """Reports handle empty data gracefully."""
    out_rel = tmp_path / "rel.md"
    out_pain = tmp_path / "pain.md"
    build_domain_relevance_report([], output_path=out_rel)
    build_pain_extraction_report([], output_path=out_pain)
    assert out_rel.exists()
    assert out_pain.exists()
