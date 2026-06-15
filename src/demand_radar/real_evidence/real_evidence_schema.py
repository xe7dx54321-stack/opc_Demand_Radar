"""Stage R1: Real Evidence Pack schemas."""
from __future__ import annotations
from pydantic import BaseModel, field_validator


class RealEvidenceItem(BaseModel):
    evidence_id: str
    target_direction_id: str
    target_direction_title_zh: str

    source_url: str | None = None
    source_note: str | None = None
    source_name: str | None = None
    source_type: str

    source_author_or_org: str | None = None
    published_at: str | None = None
    observed_at: str | None = None
    language: str = "zh"

    title: str | None = None
    raw_text: str
    evidence_quote: str | None = None

    persona: str | None = None
    persona_confidence: float | None = None
    workflow_stage: str | None = None
    pain_type: str | None = None
    evidence_type: str | None = None
    commercial_signal_type: str | None = None

    current_solution: str | None = None
    paid_alternative: str | None = None
    business_impact: str | None = None
    time_cost_signal: str | None = None
    budget_signal: str | None = None

    domain_tags: list[str] = []
    collection_query: str | None = None
    collector_note: str | None = None

    is_synthetic: bool = False
    exclude_from_scoring: bool = False

    created_at: str

    @field_validator("raw_text")
    @classmethod
    def _raw_text_nonempty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("raw_text must not be empty")
        return v


class RealEvidenceValidation(BaseModel):
    validation_id: str
    evidence_id: str

    status: str           # valid | warning | invalid | excluded
    source_quality: str   # high | medium | low | unknown
    validation_errors: list[str] = []
    validation_warnings: list[str] = []
    detected_signal_types: list[str] = []
    source_weight: float
    include_in_pipeline: bool
    created_at: str


class CalibrationReview(BaseModel):
    review_id: str
    evidence_id: str
    system_output_id: str | None = None

    human_labels: list[str]
    reviewer_note_zh: str | None = None
    suggested_prompt_fix_zh: str | None = None
    suggested_skill_fix_zh: str | None = None
    suggested_rubric_fix_zh: str | None = None
    created_at: str
