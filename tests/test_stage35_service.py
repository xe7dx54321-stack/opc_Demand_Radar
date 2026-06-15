"""Tests for Stage 3.5 UI service."""
import pytest
from datetime import datetime, timezone
from demand_radar.stage35 import stage35_store
from demand_radar.stage35.stage35_schema import (
    Stage35SelectedCandidate, Stage35RunSummary, Stage35GateResult,
)
from demand_radar.ui import stage35_service

NOW = datetime.now(timezone.utc).isoformat()


def _cand():
    return Stage35SelectedCandidate(
        selected_candidate_id="s35c_001",
        truth_score_id="ts_001",
        source_group_id="grp_001",
        group_title_zh="测试候选",
        current_truth_score=62.0,
        current_truth_level="medium",
        current_next_action="needs_more_evidence",
        selected_reason_zh="x",
        priority_rank=1,
        target_new_signals=12,
        target_evidence_intents=["paid_alternative"],
        created_at=NOW,
    )


def test_get_selected_candidates_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(stage35_store, "SELECTED_PATH", tmp_path / "none.jsonl")
    result = stage35_service.get_stage35_selected_candidates()
    assert result == []


def test_get_selected_candidates_returns_data(tmp_path, monkeypatch):
    p = tmp_path / "sel.jsonl"
    stage35_store.write_selected_candidates([_cand()], path=str(p))
    monkeypatch.setattr(stage35_store, "SELECTED_PATH", p)
    result = stage35_service.get_stage35_selected_candidates()
    assert len(result) == 1
    assert result[0].source_group_id == "grp_001"


def test_get_run_summary_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(stage35_store, "SUMMARY_PATH", tmp_path / "none.json")
    result = stage35_service.get_stage35_run_summary()
    assert result is None


def test_get_gate_result_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(stage35_store, "GATE_PATH", tmp_path / "none.json")
    result = stage35_service.get_stage35_gate_result()
    assert result is None


def test_get_gate_result_returns_data(tmp_path, monkeypatch):
    p = tmp_path / "gate.json"
    gr = Stage35GateResult(
        gate_result_id="s35gate_001",
        status="blocked",
        reason_zh="证据不足",
        required_next_action_zh="继续补充",
        created_at=NOW,
    )
    stage35_store.write_gate_result(gr, path=str(p))
    monkeypatch.setattr(stage35_store, "GATE_PATH", p)
    result = stage35_service.get_stage35_gate_result()
    assert result.status == "blocked"
