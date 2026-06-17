"""D4 review schema — second-round human calibration of D4 pain signals."""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field, field_validator

_VALID_COMMERCIAL = {"high", "medium", "low", "unclear"}
_VALID_EXTRACTION = {"good", "partial", "bad"}
_VALID_EVIDENCE = {"strong", "medium", "weak", "fake_or_insufficient"}
_VALID_ACTION = {"pursue", "watch", "reject", "needs_more_evidence"}
_VALID_ERROR_LABELS = {
    "bad_persona", "bad_workflow", "bad_pain_type", "bad_quote",
    "hallucinated_field", "missed_commercial_signal", "domain_out",
    "duplicate", "too_generic", "source_too_weak",
}


class D4PainSignalReview(BaseModel):
    review_id: str
    pain_item_id: str
    candidate_id: str | None = None
    source_url: str | None = None

    reviewer: str = "user"

    true_pain: bool | None = None
    commercial_potential: str | None = None
    evidence_quality: str | None = None
    action_decision: str | None = None
    extraction_quality: str | None = None

    error_labels: list[str] = Field(default_factory=list)
    reviewer_note_zh: str | None = None

    created_at: str
    updated_at: str | None = None

    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("commercial_potential")
    @classmethod
    def validate_commercial(cls, v: str | None) -> str | None:
        if v is not None and v not in _VALID_COMMERCIAL:
            raise ValueError(f"commercial_potential must be one of {_VALID_COMMERCIAL}")
        return v

    @field_validator("evidence_quality")
    @classmethod
    def validate_evidence(cls, v: str | None) -> str | None:
        if v is not None and v not in _VALID_EVIDENCE:
            raise ValueError(f"evidence_quality must be one of {_VALID_EVIDENCE}")
        return v

    @field_validator("action_decision")
    @classmethod
    def validate_action(cls, v: str | None) -> str | None:
        if v is not None and v not in _VALID_ACTION:
            raise ValueError(f"action_decision must be one of {_VALID_ACTION}")
        return v

    @field_validator("extraction_quality")
    @classmethod
    def validate_extraction(cls, v: str | None) -> str | None:
        if v is not None and v not in _VALID_EXTRACTION:
            raise ValueError(f"extraction_quality must be one of {_VALID_EXTRACTION}")
        return v

    @field_validator("error_labels")
    @classmethod
    def validate_error_labels(cls, v: list[str]) -> list[str]:
        invalid = set(v) - _VALID_ERROR_LABELS
        if invalid:
            raise ValueError(f"Invalid error_labels: {invalid}. Allowed: {_VALID_ERROR_LABELS}")
        return v
