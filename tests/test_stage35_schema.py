"""Tests for Stage 3.5 schemas."""
import pytest
from datetime import datetime, timezone
from demand_radar.stage35.stage35_schema import (
    Stage35SelectedCandidate, Stage35RunSummary, Stage35GateResult,
)

NOW = datetime.now(timezone.utc).isoformat()


def test_selected_candidate_valid():
    c = Stage35SelectedCandidate(
        selected_candidate_id="s35c_001",
        truth_score_id="ts_001",
        source_group_id="grp_001",
        group_title_zh="投资人AI产业跟踪",
        current_truth_score=62.0,
        current_truth_level="medium",
        current_next_action="needs_more_evidence",
        selected_reason_zh="匹配关键词",
        priority_rank=1,
        target_new_signals=12,
        target_evidence_intents=["paid_alternative", "budget_signal"],
        created_at=NOW,
    )
    assert c.current_truth_score == 62.0
    assert c.priority_rank == 1


def test_run_summary_valid():
    s = Stage35RunSummary(
        run_id="s35run_001",
        before_snapshot_name="before_stage35",
        before_snapshot_path="outputs/archive/before_stage35",
        lineage_baseline_quality="full",
        selected_candidates=2,
        template_rows=24,
        filled_signals=20,
        valid_signals=18,
        warning_signals=2,
        invalid_signals=0,
        excluded_signals=0,
        combined_rows=138,
        payment_or_cost_signals=13,
        workaround_or_current_solution_signals=6,
        business_impact_or_time_cost_signals=4,
        stage4_gate_status="blocked",
        created_at=NOW,
    )
    assert s.lineage_baseline_quality == "full"
    assert s.valid_signals == 18


def test_gate_result_valid():
    g = Stage35GateResult(
        gate_result_id="s35gate_001",
        status="blocked",
        reason_zh="证据不足",
        required_next_action_zh="继续补充证据",
        created_at=NOW,
    )
    assert g.status == "blocked"


def test_gate_result_formal():
    g = Stage35GateResult(
        gate_result_id="s35gate_002",
        status="pass_formal",
        reason_zh="满足正式门禁",
        eligible_candidates=["cand_A"],
        required_next_action_zh="进入 Stage 4",
        created_at=NOW,
    )
    assert g.status == "pass_formal"
    assert len(g.eligible_candidates) == 1


def test_gate_result_invalid_status():
    with pytest.raises(Exception):
        Stage35GateResult(
            gate_result_id="bad",
            status="invalid_status",
            reason_zh="x",
            required_next_action_zh="y",
            created_at=NOW,
        )
