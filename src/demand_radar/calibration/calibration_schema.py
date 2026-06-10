"""Schemas for Stage 1.5 extraction calibration reviews."""

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from demand_radar.state.raw_store import utc_now_iso


VALID_REVIEW_LABELS = {
    "good_extraction",
    "weak_extraction",
    "false_positive",
    "false_negative",
    "bad_quote",
    "bad_persona",
    "bad_pain_description",
    "missing_workaround",
    "missing_payment_signal",
    "should_quarantine",
}


class CalibrationReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valid_labels: ClassVar[set[str]] = VALID_REVIEW_LABELS

    review_id: str = Field(default="")
    raw_signal_id: str
    normalized_signal_id: str | None = None
    pain_point_id: str | None = None
    label: str
    reviewer_note: str
    expected_persona: str | None = None
    expected_evidence_quote: str | None = None
    expected_pain_description: str | None = None
    should_be_quarantined: bool | None = None
    created_at: str = Field(default_factory=utc_now_iso)

    @field_validator("raw_signal_id", "label", "reviewer_note", "created_at")
    @classmethod
    def required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("field must not be empty")
        return value

    @field_validator("review_id")
    @classmethod
    def optional_review_id_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("label")
    @classmethod
    def valid_label(cls, value: str) -> str:
        if value not in cls.valid_labels:
            raise ValueError(f"unsupported calibration label: {value}")
        return value
