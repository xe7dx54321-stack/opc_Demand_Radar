"""Truth Scoring schemas for Stage 3."""
from __future__ import annotations

from pydantic import BaseModel, field_validator

VALID_TRUTH_LEVELS = {"strong", "medium", "weak", "insufficient"}
VALID_NEXT_ACTIONS = {
    "proceed_to_fit_scoring",
    "needs_more_evidence",
    "keep_watch",
    "discard",
}
VALID_TRUTH_DIMENSIONS = {
    "pain_evidence_strength",
    "frequency_repetition",
    "existing_workaround",
    "willingness_to_pay",
    "persona_clarity",
}
VALID_REVIEW_LABELS = {
    "score_reasonable",
    "score_too_high",
    "score_too_low",
    "bad_evidence",
    "bad_persona",
    "needs_more_evidence",
    "should_discard",
    "should_enter_fit_scoring",
}


class TruthScore(BaseModel):
    truth_score_id: str

    source_type: str
    source_group_id: str
    group_title_zh: str
    group_summary_zh: str

    truth_score: float
    truth_level: str

    dimension_scores: dict[str, float]

    evidence_count: int
    source_count: int

    personas: list[str] = []
    domain_tags: list[str] = []

    positive_signals: list[str] = []
    negative_signals: list[str] = []
    risk_flags: list[str] = []

    scoring_reason_zh: str
    recommended_next_action: str

    created_at: str

    @field_validator("truth_score")
    @classmethod
    def validate_truth_score(cls, v: float) -> float:
        if not (0.0 <= v <= 100.0):
            raise ValueError(f"truth_score must be 0-100, got {v}")
        return round(v, 2)

    @field_validator("truth_level")
    @classmethod
    def validate_truth_level(cls, v: str) -> str:
        if v not in VALID_TRUTH_LEVELS:
            raise ValueError(f"truth_level must be one of {VALID_TRUTH_LEVELS}, got {v!r}")
        return v

    @field_validator("recommended_next_action")
    @classmethod
    def validate_next_action(cls, v: str) -> str:
        if v not in VALID_NEXT_ACTIONS:
            raise ValueError(f"recommended_next_action must be one of {VALID_NEXT_ACTIONS}, got {v!r}")
        return v

    @field_validator("dimension_scores")
    @classmethod
    def validate_dimensions(cls, v: dict[str, float]) -> dict[str, float]:
        missing = VALID_TRUTH_DIMENSIONS - set(v.keys())
        if missing:
            raise ValueError(f"dimension_scores missing required dimensions: {missing}")
        for dim, score in v.items():
            if not (0.0 <= score <= 100.0):
                raise ValueError(f"dimension {dim} score out of range: {score}")
        return v

    @field_validator("scoring_reason_zh")
    @classmethod
    def validate_scoring_reason(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("scoring_reason_zh must not be empty")
        return v


class TruthScoreReview(BaseModel):
    review_id: str
    truth_score_id: str
    source_group_id: str

    label: str
    reviewer_note: str | None = None
    corrected_truth_level: str | None = None
    corrected_next_action: str | None = None

    created_at: str

    @field_validator("label")
    @classmethod
    def validate_label(cls, v: str) -> str:
        if v not in VALID_REVIEW_LABELS:
            raise ValueError(f"label must be one of {VALID_REVIEW_LABELS}, got {v!r}")
        return v

    @field_validator("corrected_truth_level")
    @classmethod
    def validate_corrected_level(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_TRUTH_LEVELS:
            raise ValueError(f"corrected_truth_level must be one of {VALID_TRUTH_LEVELS}, got {v!r}")
        return v

    @field_validator("corrected_next_action")
    @classmethod
    def validate_corrected_action(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_NEXT_ACTIONS:
            raise ValueError(f"corrected_next_action must be one of {VALID_NEXT_ACTIONS}, got {v!r}")
        return v
