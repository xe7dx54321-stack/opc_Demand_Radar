"""Schemas for MVP-D2 expansion diagnostics."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


RawTextQuality = Literal["too_thin", "adequate", "rich"]
SourceQuality = Literal["high", "medium", "low"]
CandidateUsefulness = Literal[
    "useful_for_demand",
    "useful_for_competitor_map",
    "useful_for_market_context",
    "not_useful",
]
RejectCategory = Literal[
    "domain_out",
    "product_marketing",
    "technical_issue_not_business_pain",
    "generic_article",
    "raw_text_too_thin",
    "no_user_persona",
    "no_workflow",
    "no_pain",
    "no_evidence_quote",
    "duplicate_or_near_duplicate",
    "source_low_quality",
    "prompt_too_strict_possible",
    "unknown",
]

VALID_REJECT_CATEGORIES = {
    "domain_out",
    "product_marketing",
    "technical_issue_not_business_pain",
    "generic_article",
    "raw_text_too_thin",
    "no_user_persona",
    "no_workflow",
    "no_pain",
    "no_evidence_quote",
    "duplicate_or_near_duplicate",
    "source_low_quality",
    "prompt_too_strict_possible",
    "unknown",
}


class RejectDiagnosticItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    diagnostic_id: str
    candidate_id: str
    seed_id: str | None = None
    pain_item_id: str | None = None
    query_id: str | None = None
    query: str | None = None
    query_type: str | None = None

    title: str | None = None
    source_url: str | None = None
    source_type: str | None = None
    connector: str | None = None

    raw_text_chars: int
    raw_text_quality: RawTextQuality

    llm_should_extract: bool
    llm_reject_reason: str | None = None

    reject_category: RejectCategory
    source_quality: SourceQuality
    candidate_usefulness: CandidateUsefulness

    diagnostic_note_zh: str
    created_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("diagnostic_id", "candidate_id", "raw_text_quality", "reject_category", "source_quality", "candidate_usefulness", "diagnostic_note_zh", "created_at")
    @classmethod
    def required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("field must not be empty")
        return value

    @field_validator("raw_text_chars")
    @classmethod
    def raw_text_chars_not_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("raw_text_chars must be non-negative")
        return value


class SourceQualityScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score_id: str
    source_type: str
    connector: str
    total_candidates: int = 0
    gate_allowed: int = 0
    llm_processed: int = 0
    should_extract_true: int = 0
    reject_count: int = 0
    yield_rate: float = 0.0
    dominant_reject_reason: str | None = None
    source_quality_score: float = 0.0
    source_strategy_recommendation: str
    created_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("yield_rate", "source_quality_score")
    @classmethod
    def score_between_zero_and_one(cls, value: float) -> float:
        if value < 0 or value > 1:
            raise ValueError("score must be between 0 and 1")
        return value


class MVPD2RunSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain_id: str
    generated_at: str
    radar_commit: str = "unknown"
    foundation_commit: str = "unknown"
    provider: str = "none"
    model: str = "none"
    real_llm_run: bool = False
    cache_enabled: bool = True

    mvp_d_selected_for_llm: int = 0
    mvp_d_should_extract_true: int = 0
    mvp_d_reject_count: int = 0

    total_rejected: int = 0
    generated_v2_queries: int = 0

    ran_pilot: bool = False
    blocked_reason: str | None = None
    raw_new_signals: int = 0
    unique_new_signals: int = 0
    gate_allowed: int = 0
    selected_for_llm: int = 0
    should_extract_true: int = 0
    yield_rate: float = 0.0

    comparison_result: str = "blocked"
    engineering_acceptance: str
    product_acceptance: str
    can_rerun_seeded_expansion: bool
    can_enter_second_review: bool
    can_enter_foundation_source_upgrade: bool
    reason: str
    metadata: dict[str, Any] = Field(default_factory=dict)
