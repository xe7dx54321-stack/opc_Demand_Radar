"""Schemas for Stage 3.4 Candidate Lineage & Targeted Evidence Attribution."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, field_validator

VALID_MATCH_STRENGTHS = {"strong", "weak", "unmatched", "split", "merged", "missing_baseline"}
VALID_ATTRIBUTION_STATUSES = {
    "attributed_to_expected_group", "attributed_to_related_group",
    "not_used", "lost_in_extraction", "lost_in_clustering",
    "lost_in_merge", "excluded_or_invalid",
}
VALID_DELTA_CONFIDENCES = {"high", "medium", "low"}
VALID_NEXT_ACTIONS = {
    "proceed_to_fit_scoring", "collect_more_targeted_evidence",
    "stabilize_lineage", "keep_watch",
}


class CandidateLineage(BaseModel):
    lineage_id: str
    before_truth_score_id: Optional[str] = None
    before_group_id: Optional[str] = None
    before_group_title_zh: Optional[str] = None
    before_truth_score: Optional[float] = None
    before_truth_level: Optional[str] = None
    before_next_action: Optional[str] = None
    after_truth_score_id: Optional[str] = None
    after_group_id: Optional[str] = None
    after_group_title_zh: Optional[str] = None
    after_truth_score: Optional[float] = None
    after_truth_level: Optional[str] = None
    after_next_action: Optional[str] = None
    match_score: float = 0.0
    match_strength: str
    match_reasons: list[str] = []
    targeted_signal_ids: list[str] = []
    matched_targeted_signal_ids: list[str] = []
    unmatched_targeted_signal_ids: list[str] = []
    drift_flags: list[str] = []
    lineage_summary_zh: str
    created_at: str

    @field_validator("match_strength")
    @classmethod
    def validate_match_strength(cls, v: str) -> str:
        if v not in VALID_MATCH_STRENGTHS:
            raise ValueError(f"match_strength must be one of {VALID_MATCH_STRENGTHS}")
        return v


class TargetedEvidenceAttribution(BaseModel):
    attribution_id: str
    target_signal_id: str
    target_group_id: Optional[str] = None
    target_truth_score_id: Optional[str] = None
    target_group_title_zh: Optional[str] = None
    evidence_intent: Optional[str] = None
    raw_signal_id: Optional[str] = None
    pain_point_id: Optional[str] = None
    demand_cluster_ids: list[str] = []
    reviewed_group_ids: list[str] = []
    truth_score_ids: list[str] = []
    attribution_status: str
    attribution_confidence: float
    attribution_reason_zh: str
    created_at: str

    @field_validator("attribution_status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in VALID_ATTRIBUTION_STATUSES:
            raise ValueError(f"attribution_status must be one of {VALID_ATTRIBUTION_STATUSES}")
        return v


class StableTruthScoreDelta(BaseModel):
    stable_delta_id: str
    lineage_id: str
    before_group_title_zh: Optional[str] = None
    after_group_title_zh: Optional[str] = None
    before_truth_score: Optional[float] = None
    after_truth_score: Optional[float] = None
    stable_delta: Optional[float] = None
    before_truth_level: Optional[str] = None
    after_truth_level: Optional[str] = None
    delta_confidence: str
    improvement_dimensions: list[str] = []
    remaining_gaps: list[str] = []
    drift_flags: list[str] = []
    interpretation_zh: str
    recommended_next_action: str
    created_at: str

    @field_validator("delta_confidence")
    @classmethod
    def validate_confidence(cls, v: str) -> str:
        if v not in VALID_DELTA_CONFIDENCES:
            raise ValueError(f"delta_confidence must be one of {VALID_DELTA_CONFIDENCES}")
        return v

    @field_validator("recommended_next_action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        if v not in VALID_NEXT_ACTIONS:
            raise ValueError(f"recommended_next_action must be one of {VALID_NEXT_ACTIONS}")
        return v
