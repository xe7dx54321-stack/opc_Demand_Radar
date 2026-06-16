"""MVP-C: Review schema for pain signal human calibration."""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, field_validator, model_validator

_VALID_COMMERCIAL = {"high", "medium", "low", "unclear"}
_VALID_EXTRACTION = {"good", "partial", "bad"}
_VALID_DOMAIN_REL = {"good", "too_loose", "too_strict", "wrong_domain"}
_VALID_EVIDENCE = {"strong", "medium", "weak", "fake_or_insufficient"}
_VALID_ACTION = {"pursue", "watch", "reject", "needs_more_evidence"}
_VALID_ERROR_LABELS = {
    "bad_persona", "bad_workflow", "bad_pain_type", "bad_quote",
    "hallucinated_field", "missed_commercial_signal", "domain_out",
    "duplicate", "too_generic", "source_too_weak",
}


class PainSignalReview(BaseModel):
    review_id: str
    pain_item_id: str
    candidate_id: str

    reviewer: str = "user"

    true_pain: bool | None = None
    commercial_potential: str | None = None
    extraction_quality: str | None = None
    domain_relevance_quality: str | None = None
    evidence_quality: str | None = None
    action_decision: str | None = None

    error_labels: list[str] = []

    reviewer_note_zh: str | None = None
    suggested_prompt_fix_zh: str | None = None
    suggested_rule_fix_zh: str | None = None
    suggested_source_weight_fix_zh: str | None = None

    created_at: str
    updated_at: str | None = None

    metadata: dict[str, Any] = {}

    @field_validator("commercial_potential")
    @classmethod
    def validate_commercial(cls, v: str | None) -> str | None:
        if v is not None and v not in _VALID_COMMERCIAL:
            raise ValueError(f"commercial_potential must be one of {_VALID_COMMERCIAL}, got {v!r}")
        return v

    @field_validator("extraction_quality")
    @classmethod
    def validate_extraction(cls, v: str | None) -> str | None:
        if v is not None and v not in _VALID_EXTRACTION:
            raise ValueError(f"extraction_quality must be one of {_VALID_EXTRACTION}, got {v!r}")
        return v

    @field_validator("domain_relevance_quality")
    @classmethod
    def validate_domain_rel(cls, v: str | None) -> str | None:
        if v is not None and v not in _VALID_DOMAIN_REL:
            raise ValueError(f"domain_relevance_quality must be one of {_VALID_DOMAIN_REL}, got {v!r}")
        return v

    @field_validator("evidence_quality")
    @classmethod
    def validate_evidence(cls, v: str | None) -> str | None:
        if v is not None and v not in _VALID_EVIDENCE:
            raise ValueError(f"evidence_quality must be one of {_VALID_EVIDENCE}, got {v!r}")
        return v

    @field_validator("action_decision")
    @classmethod
    def validate_action(cls, v: str | None) -> str | None:
        if v is not None and v not in _VALID_ACTION:
            raise ValueError(f"action_decision must be one of {_VALID_ACTION}, got {v!r}")
        return v

    @field_validator("error_labels")
    @classmethod
    def validate_error_labels(cls, v: list[str]) -> list[str]:
        invalid = set(v) - _VALID_ERROR_LABELS
        if invalid:
            raise ValueError(f"Invalid error_labels: {invalid}. Allowed: {_VALID_ERROR_LABELS}")
        return v


class PainSignalReviewSummary(BaseModel):
    total_pain_items: int
    reviewed_count: int
    unreviewed_count: int

    true_pain_count: int = 0
    false_pain_count: int = 0
    true_pain_unclear_count: int = 0

    commercial_high_count: int = 0
    commercial_medium_count: int = 0
    commercial_low_count: int = 0
    commercial_unclear_count: int = 0

    pursue_count: int = 0
    watch_count: int = 0
    reject_count: int = 0
    needs_more_evidence_count: int = 0

    extraction_good_count: int = 0
    extraction_partial_count: int = 0
    extraction_bad_count: int = 0

    top_error_labels: dict[str, int] = {}
