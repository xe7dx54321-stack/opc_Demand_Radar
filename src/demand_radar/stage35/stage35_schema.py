"""Stage 3.5 Pydantic schemas."""
from __future__ import annotations
from pydantic import BaseModel, field_validator


class Stage35SelectedCandidate(BaseModel):
    selected_candidate_id: str
    truth_score_id: str
    source_group_id: str
    group_title_zh: str
    current_truth_score: float
    current_truth_level: str
    current_next_action: str
    selected_reason_zh: str
    priority_rank: int
    target_new_signals: int
    target_evidence_intents: list[str]
    created_at: str


class Stage35RunSummary(BaseModel):
    run_id: str
    before_snapshot_name: str
    before_snapshot_path: str
    lineage_baseline_quality: str
    selected_candidates: int
    template_rows: int
    filled_signals: int
    valid_signals: int
    warning_signals: int
    invalid_signals: int
    excluded_signals: int
    combined_rows: int
    payment_or_cost_signals: int
    workaround_or_current_solution_signals: int
    business_impact_or_time_cost_signals: int
    attribution_rate: float | None = None
    stable_delta_improved: int | None = None
    stable_proceed_to_fit_scoring: int | None = None
    stage4_gate_status: str | None = None
    created_at: str


class Stage35GateResult(BaseModel):
    gate_result_id: str
    status: str
    reason_zh: str
    eligible_candidates: list[str] = []
    tentative_candidates: list[str] = []
    blocked_candidates: list[str] = []
    required_next_action_zh: str
    created_at: str

    @field_validator("status")
    @classmethod
    def _valid_status(cls, v: str) -> str:
        allowed = {"pass_formal", "pass_tentative", "blocked"}
        if v not in allowed:
            raise ValueError(f"status must be one of {allowed}")
        return v
