"""MVP-B: Extracted pain item schema."""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, field_validator, model_validator


class ExtractedPainItem(BaseModel):
    pain_item_id: str
    candidate_id: str

    should_extract: bool
    reject_reason: str | None = None

    persona: str | None = None
    persona_confidence: float | None = None
    workflow_stage: str | None = None
    job_to_be_done: str | None = None

    pain_type: str | None = None
    pain_description_zh: str | None = None
    evidence_quote: str | None = None

    current_solution: str | None = None
    paid_alternative: str | None = None
    business_impact: str | None = None
    time_cost_signal: str | None = None
    budget_signal: str | None = None

    commercial_signal_type: str | None = None
    evidence_strength: str

    confidence: float

    reasoning_summary_zh: str | None = None

    source_url: str | None = None
    source_type: str | None = None
    title: str | None = None

    prompt_version: str = "pain_extraction_v1"
    model: str | None = None
    created_at: str

    metadata: dict[str, Any] = {}

    @field_validator("confidence")
    @classmethod
    def confidence_in_range(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"confidence must be 0-1, got {v}")
        return v

    @field_validator("reject_reason")
    @classmethod
    def reject_needs_reason(cls, v, info) -> str | None:
        data = info.data
        if not data.get("should_extract") and not v:
            raise ValueError("reject_reason required when should_extract=false")
        return v

    @field_validator("evidence_quote")
    @classmethod
    def extract_needs_quote(cls, v, info) -> str | None:
        data = info.data
        if data.get("should_extract") and not v:
            raise ValueError("evidence_quote required when should_extract=true")
        return v

    @model_validator(mode="after")
    def strong_evidence_completeness(self) -> "ExtractedPainItem":
        if self.evidence_strength == "strong":
            missing = []
            if not self.persona:
                missing.append("persona")
            if not self.workflow_stage:
                missing.append("workflow_stage")
            if not self.pain_description_zh:
                missing.append("pain_description_zh")
            if not self.evidence_quote:
                missing.append("evidence_quote")
            if missing:
                raise ValueError(f"strong evidence requires: {missing}")
        return self