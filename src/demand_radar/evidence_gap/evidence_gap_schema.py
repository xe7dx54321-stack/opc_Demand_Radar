"""Evidence Gap Analysis schemas for Stage 3.2."""
from __future__ import annotations
from pydantic import BaseModel, field_validator

VALID_PRIORITY = {"high", "medium", "low"}
VALID_MISSING_EVIDENCE_TYPES = {
    "frequency_signal", "source_diversity", "paid_alternative",
    "budget_signal", "manual_workaround", "persona_specificity",
    "concrete_pain_quote", "repeated_workflow", "business_impact",
    "urgency_signal", "current_solution", "stronger_pain_evidence",
    "target_role_clarity", "time_cost",
}
VALID_DIMENSIONS = {
    "pain_evidence_strength", "frequency_repetition",
    "existing_workaround", "willingness_to_pay", "persona_clarity",
}


class EvidenceGapAnalysis(BaseModel):
    gap_analysis_id: str
    truth_score_id: str
    source_group_id: str
    group_title_zh: str
    current_truth_score: float
    current_truth_level: str
    current_next_action: str
    dimension_scores: dict[str, float]
    missing_evidence_types: list[str]
    main_bottleneck_dimensions: list[str]
    gap_reason_zh: str
    upgrade_path_zh: str
    target_new_signals: int
    priority: str
    created_at: str

    @field_validator("missing_evidence_types")
    @classmethod
    def validate_missing(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("missing_evidence_types must not be empty")
        return v

    @field_validator("gap_reason_zh")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("gap_reason_zh must not be empty")
        return v

    @field_validator("upgrade_path_zh")
    @classmethod
    def validate_path(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("upgrade_path_zh must not be empty")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        if v not in VALID_PRIORITY:
            raise ValueError(f"priority must be one of {VALID_PRIORITY}, got {v!r}")
        return v


class TargetedSignalCollectionPlan(BaseModel):
    plan_id: str
    gap_analysis_id: str
    truth_score_id: str
    source_group_id: str
    group_title_zh: str
    target_new_signals: int
    target_personas: list[str] = []
    target_source_types: list[str] = []
    target_languages: list[str] = []
    search_keywords_zh: list[str] = []
    search_keywords_en: list[str] = []
    positive_signal_criteria: list[str] = []
    negative_signal_criteria: list[str] = []
    collection_notes_zh: str
    expected_impact_zh: str
    created_at: str

    @field_validator("search_keywords_zh", "search_keywords_en")
    @classmethod
    def validate_keywords(cls, v: list[str]) -> list[str]:
        return v

    @field_validator("positive_signal_criteria")
    @classmethod
    def validate_positive(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("positive_signal_criteria must not be empty")
        return v

    @field_validator("negative_signal_criteria")
    @classmethod
    def validate_negative(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("negative_signal_criteria must not be empty")
        return v

    @field_validator("collection_notes_zh")
    @classmethod
    def validate_notes(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("collection_notes_zh must not be empty")
        return v
