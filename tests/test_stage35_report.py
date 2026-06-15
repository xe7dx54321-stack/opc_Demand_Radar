"""Tests for Stage 3.5 reports."""
import pytest
from pathlib import Path
from demand_radar.stage35.stage35_report import (
    build_stage35_expansion_report,
    build_stage35_stable_delta_report,
    build_stage35_gate_report,
)


def test_expansion_report_created(tmp_path):
    out = tmp_path / "report.md"
    build_stage35_expansion_report(None, [], [], output_path=out)
    assert out.exists()
    assert "Stage 3.5" in out.read_text(encoding="utf-8")


def test_expansion_report_shows_candidates(tmp_path):
    out = tmp_path / "report.md"
    cands = [{"group_title_zh": "投资人AI产业跟踪", "current_truth_score": 62.0,
              "current_truth_level": "medium", "current_next_action": "needs_more_evidence",
              "selected_reason_zh": "匹配", "target_new_signals": 12,
              "target_evidence_intents": ["paid_alternative"]}]
    build_stage35_expansion_report(None, cands, [], output_path=out)
    content = out.read_text(encoding="utf-8")
    assert "投资人AI产业跟踪" in content


def test_expansion_report_shows_validation_errors(tmp_path):
    out = tmp_path / "report.md"
    vals = [{"status": "invalid", "target_signal_id": "s35_001",
             "validation_errors": ["raw_text too short"]}]
    build_stage35_expansion_report(None, [], vals, output_path=out)
    content = out.read_text(encoding="utf-8")
    assert "raw_text too short" in content


def test_stable_delta_report_created(tmp_path):
    out = tmp_path / "delta.md"
    build_stage35_stable_delta_report([], output_path=out)
    assert out.exists()
    assert "Delta" in out.read_text(encoding="utf-8")


def test_stable_delta_report_shows_data(tmp_path):
    out = tmp_path / "delta.md"
    deltas = [{
        "after_group_title_zh": "企业知识工作流",
        "before_truth_score": 62.0, "after_truth_score": 71.0,
        "stable_delta": 9.0, "delta_confidence": "medium",
        "drift_flags": [], "recommended_next_action": "collect_more_targeted_evidence",
        "interpretation_zh": "有所改善",
    }]
    build_stage35_stable_delta_report(deltas, output_path=out)
    content = out.read_text(encoding="utf-8")
    assert "企业知识工作流" in content
    assert "9.0" in content


def test_gate_report_created(tmp_path):
    out = tmp_path / "gate.md"
    build_stage35_gate_report(None, output_path=out)
    assert out.exists()
    assert "Gate" in out.read_text(encoding="utf-8")


def test_gate_report_shows_status(tmp_path):
    out = tmp_path / "gate.md"
    gr = {"status": "pass_tentative", "reason_zh": "分数足够",
          "required_next_action_zh": "进入", "eligible_candidates": [],
          "tentative_candidates": ["企业知识"], "blocked_candidates": []}
    build_stage35_gate_report(gr, output_path=out)
    content = out.read_text(encoding="utf-8")
    assert "pass_tentative" in content
    assert "企业知识" in content
