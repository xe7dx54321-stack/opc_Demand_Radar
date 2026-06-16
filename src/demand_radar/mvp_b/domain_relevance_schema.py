"""MVP-B: Domain relevance result schema."""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, field_validator


class DomainRelevanceResult(BaseModel):
    result_id: str
    candidate_id: str

    relevance_decision: str
    # include | uncertain | exclude

    relevance_score: float

    matched_persona: str | None = None
    matched_workflow: str | None = None

    domain_reason_zh: str | None = None
    exclude_reason_zh: str | None = None

    source_type: str | None = None
    source_url: str | None = None

    prompt_version: str = "rule_only"
    model: str | None = None

    created_at: str
    metadata: dict[str, Any] = {}

    @field_validator("relevance_score")
    @classmethod
    def score_in_range(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"relevance_score must be 0-1, got {v}")
        return v

    @field_validator("exclude_reason_zh")
    @classmethod
    def exclude_needs_reason(cls, v, info) -> str | None:
        data = info.data
        if data.get("relevance_decision") == "exclude" and not v:
            raise ValueError("exclude_reason_zh is required when relevance_decision=exclude")
        return v

    @field_validator("domain_reason_zh")
    @classmethod
    def include_needs_reason(cls, v, info) -> str | None:
        data = info.data
        if data.get("relevance_decision") == "include" and not v:
            raise ValueError("domain_reason_zh is required when relevance_decision=include")
        return v