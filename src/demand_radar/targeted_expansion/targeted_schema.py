"""Schemas for Stage 3.3 Targeted Evidence Expansion."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, field_validator

VALID_COLLECTION_STATUS = {"pending", "collected", "skipped", "invalid"}
VALID_VALIDATION_STATUS = {"valid", "warning", "invalid", "excluded"}
VALID_EVIDENCE_INTENTS = {
    "paid_alternative", "budget_signal", "manual_workaround",
    "current_solution", "business_impact", "time_cost",
    "product_review", "case_study",
}


class TargetedSignalTemplateRow(BaseModel):
    target_signal_id: str
    target_group_id: str
    target_group_title_zh: str
    target_truth_score_id: Optional[str] = None
    target_current_score: Optional[float] = None
    target_gap_types: list[str] = []
    evidence_intent: str
    desired_source_type: Optional[str] = None
    desired_language: Optional[str] = None
    suggested_keywords: list[str] = []
    title: Optional[str] = None
    raw_text: Optional[str] = None
    url: Optional[str] = None
    source_name: Optional[str] = None
    source_type: Optional[str] = None
    published_at: Optional[str] = None
    language: Optional[str] = None
    domain_tags: list[str] = []
    batch_id: str = "batch_stage33_targeted"
    source_note: Optional[str] = None
    signal_focus: Optional[str] = None
    expected_quality: Optional[str] = None
    is_synthetic: bool = False
    exclude_from_truth_scoring: bool = False
    collection_status: str = "pending"
    collector_note: Optional[str] = None

    @field_validator("collection_status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in VALID_COLLECTION_STATUS:
            raise ValueError(f"collection_status must be one of {VALID_COLLECTION_STATUS}")
        return v


class TargetedSignalValidation(BaseModel):
    validation_id: str
    target_signal_id: str
    target_group_id: Optional[str] = None
    evidence_intent: Optional[str] = None
    status: str
    validation_errors: list[str] = []
    validation_warnings: list[str] = []
    matched_gap_types: list[str] = []
    detected_signal_types: list[str] = []
    include_in_combined_input: bool
    created_at: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in VALID_VALIDATION_STATUS:
            raise ValueError(f"status must be one of {VALID_VALIDATION_STATUS}")
        return v


class TruthScoreDelta(BaseModel):
    source_group_id: str
    group_title_zh: str
    before_truth_score: Optional[float] = None
    after_truth_score: Optional[float] = None
    delta: Optional[float] = None
    before_truth_level: Optional[str] = None
    after_truth_level: Optional[str] = None
    before_next_action: Optional[str] = None
    after_next_action: Optional[str] = None
    improved_dimensions: list[str] = []
    remaining_gaps: list[str] = []
    created_at: str


class TargetedExpansionSummary(BaseModel):
    template_rows: int = 0
    filled_signals: int = 0
    valid_signals: int = 0
    warning_signals: int = 0
    invalid_signals: int = 0
    excluded_synthetic: int = 0
    combined_input_rows: int = 0
    base_rows: int = 0
    targeted_rows_included: int = 0
    duplicates_removed: int = 0
    created_at: str
