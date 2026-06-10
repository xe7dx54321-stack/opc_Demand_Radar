"""Demand cluster schema for Stage 2 candidate state."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from demand_radar.state.raw_store import utc_now_iso


class DemandCluster(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cluster_id: str = Field(default="")
    cluster_title_zh: str
    cluster_summary_zh: str

    personas: list[str] = Field(default_factory=list)
    domain_tags: list[str] = Field(default_factory=list)
    workflow_family: str | None = None
    batch_ids: list[str] = Field(default_factory=list)
    signal_focuses: list[str] = Field(default_factory=list)
    expected_quality_mix: dict[str, int] = Field(default_factory=dict)

    related_pain_point_ids: list[str]
    evidence_count: int
    source_count: int

    representative_pain_descriptions: list[str] = Field(default_factory=list)
    representative_quotes: list[str] = Field(default_factory=list)
    current_workarounds: list[str] = Field(default_factory=list)

    cluster_confidence: float
    cluster_method: str
    created_at: str = Field(default_factory=utc_now_iso)

    @field_validator("cluster_id")
    @classmethod
    def optional_cluster_id_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("cluster_title_zh", "cluster_summary_zh", "cluster_method", "created_at")
    @classmethod
    def required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("field must not be empty")
        return value

    @field_validator("cluster_title_zh", "cluster_summary_zh")
    @classmethod
    def chinese_text_required(cls, value: str) -> str:
        if not any("\u4e00" <= char <= "\u9fff" for char in value):
            raise ValueError("cluster title and summary must contain Chinese text")
        return value

    @field_validator("related_pain_point_ids")
    @classmethod
    def related_pain_points_required(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if not cleaned:
            raise ValueError("related_pain_point_ids must not be empty")
        return cleaned

    @field_validator("cluster_confidence")
    @classmethod
    def confidence_between_zero_and_one(cls, value: float) -> float:
        if value < 0 or value > 1:
            raise ValueError("cluster_confidence must be between 0 and 1")
        return value

    @model_validator(mode="after")
    def validate_counts(self) -> "DemandCluster":
        if self.evidence_count != len(self.related_pain_point_ids):
            raise ValueError("evidence_count must equal related_pain_point_ids length")
        if self.evidence_count < 1:
            raise ValueError("evidence_count must be at least 1")
        if self.source_count < 1:
            raise ValueError("source_count must be at least 1")
        return self
