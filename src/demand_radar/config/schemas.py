"""Pydantic schemas for Stage 1 pipeline state."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


JsonDict = dict[str, Any]


class RawSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw_signal_id: str
    source_name: str
    source_type: str
    title: str
    raw_text: str
    url: str | None = None
    published_at: str | None = None
    collected_at: str
    language: str | None = None
    domain_tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    content_hash: str

    @field_validator("raw_signal_id", "source_name", "source_type", "title", "raw_text", "collected_at", "content_hash")
    @classmethod
    def required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("field must not be empty")
        return value


class NormalizedSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw_signal_id: str
    normalized_signal_id: str
    source_name: str
    title: str
    normalized_text: str
    url: str | None = None
    language: str | None = None
    domain_tags: list[str] = Field(default_factory=list)
    content_hash: str

    @field_validator("raw_signal_id", "normalized_signal_id", "source_name", "title", "normalized_text", "content_hash")
    @classmethod
    def required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("field must not be empty")
        return value


class PainPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pain_point_id: str
    raw_signal_id: str
    normalized_signal_id: str
    persona: str | None = None
    scenario: str | None = None
    job_to_be_done: str | None = None
    current_workaround: str | None = None
    pain_description: str
    pain_intensity: int | None = None
    frequency_signal: str | None = None
    payment_signal: str | None = None
    evidence_quote: str
    evidence_span: str | None = None
    confidence: float
    extraction_mode: str
    extraction_notes: str | None = None

    @field_validator("pain_point_id", "raw_signal_id", "normalized_signal_id", "pain_description", "evidence_quote", "extraction_mode")
    @classmethod
    def required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("field must not be empty")
        return value

    @field_validator("confidence")
    @classmethod
    def confidence_between_zero_and_one(cls, value: float) -> float:
        if value < 0 or value > 1:
            raise ValueError("confidence must be between 0 and 1")
        return value

    @field_validator("pain_intensity")
    @classmethod
    def pain_intensity_between_one_and_five(cls, value: int | None) -> int | None:
        if value is not None and not 1 <= value <= 5:
            raise ValueError("pain_intensity must be between 1 and 5")
        return value


class QuarantineRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quarantine_id: str
    item_type: str
    item_id: str | None = None
    reason: str
    raw_payload: dict[str, Any]
    created_at: str

    @field_validator("quarantine_id", "item_type", "reason", "created_at")
    @classmethod
    def required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("field must not be empty")
        return value


class RunSummary(BaseModel):
    raw_signals: int
    normalized_signals: int
    pain_points: int
    quarantined_items: int
    generated_at: str
