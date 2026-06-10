"""Schemas for Stage 2.5 cluster merge suggestions and reviewed groups."""

from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from demand_radar.state.raw_store import utc_now_iso


MergeStrength = Literal["strong", "medium", "weak"]

VALID_CLUSTER_GROUP_REVIEW_LABELS = {
    "confirm_merge",
    "reject_merge",
    "maybe_merge",
    "wrong_reason",
    "bad_title",
    "needs_split",
    "duplicate_candidate",
    "not_same_demand",
}


class ClusterMergeCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    merge_candidate_id: str
    cluster_id_a: str
    cluster_id_b: str
    title_a: str
    title_b: str
    similarity_score: float
    strength: MergeStrength
    field_scores: dict[str, float] = Field(default_factory=dict)
    shared_personas: list[str] = Field(default_factory=list)
    shared_domain_tags: list[str] = Field(default_factory=list)
    shared_keywords: list[str] = Field(default_factory=list)
    batch_ids: list[str] = Field(default_factory=list)
    merge_reason_zh: str
    risk_note_zh: str | None = None
    representative_quotes_a: list[str] = Field(default_factory=list)
    representative_quotes_b: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)

    @field_validator(
        "merge_candidate_id",
        "cluster_id_a",
        "cluster_id_b",
        "title_a",
        "title_b",
        "strength",
        "merge_reason_zh",
        "created_at",
    )
    @classmethod
    def required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("field must not be empty")
        return value

    @field_validator("similarity_score")
    @classmethod
    def score_between_zero_and_one_hundred(cls, value: float) -> float:
        if value < 0 or value > 100:
            raise ValueError("similarity_score must be between 0 and 100")
        return value

    @field_validator("merge_reason_zh")
    @classmethod
    def reason_must_be_chinese(cls, value: str) -> str:
        if not any("\u4e00" <= char <= "\u9fff" for char in value):
            raise ValueError("merge_reason_zh must contain Chinese text")
        return value

    @model_validator(mode="after")
    def different_clusters_required(self) -> "ClusterMergeCandidate":
        if self.cluster_id_a == self.cluster_id_b:
            raise ValueError("cluster_id_a and cluster_id_b must be different")
        return self


class ClusterGroupReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valid_labels: ClassVar[set[str]] = VALID_CLUSTER_GROUP_REVIEW_LABELS

    review_id: str
    merge_candidate_id: str
    cluster_id_a: str
    cluster_id_b: str
    label: str
    reviewer_note: str | None = None
    expected_group_title_zh: str | None = None
    expected_group_summary_zh: str | None = None
    created_at: str = Field(default_factory=utc_now_iso)

    @field_validator("review_id", "merge_candidate_id", "cluster_id_a", "cluster_id_b", "label", "created_at")
    @classmethod
    def required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("field must not be empty")
        return value

    @field_validator("label")
    @classmethod
    def valid_label(cls, value: str) -> str:
        if value not in cls.valid_labels:
            raise ValueError(f"unsupported cluster group review label: {value}")
        return value

    @model_validator(mode="after")
    def different_clusters_required(self) -> "ClusterGroupReview":
        if self.cluster_id_a == self.cluster_id_b:
            raise ValueError("cluster_id_a and cluster_id_b must be different")
        return self


class ReviewedClusterGroup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    group_id: str
    group_title_zh: str
    group_summary_zh: str
    cluster_ids: list[str]
    related_pain_point_ids: list[str]
    personas: list[str] = Field(default_factory=list)
    domain_tags: list[str] = Field(default_factory=list)
    batch_ids: list[str] = Field(default_factory=list)
    evidence_count: int
    source_count: int
    representative_pain_descriptions: list[str] = Field(default_factory=list)
    representative_quotes: list[str] = Field(default_factory=list)
    current_workarounds: list[str] = Field(default_factory=list)
    created_from_review_ids: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)

    @field_validator("group_id", "group_title_zh", "group_summary_zh", "created_at")
    @classmethod
    def required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("field must not be empty")
        return value

    @field_validator("group_title_zh", "group_summary_zh")
    @classmethod
    def chinese_text_required(cls, value: str) -> str:
        if not any("\u4e00" <= char <= "\u9fff" for char in value):
            raise ValueError("group title and summary must contain Chinese text")
        return value

    @field_validator("cluster_ids", "related_pain_point_ids")
    @classmethod
    def non_empty_unique_ids(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        for item in value:
            text = item.strip()
            if text and text not in cleaned:
                cleaned.append(text)
        if not cleaned:
            raise ValueError("id list must not be empty")
        return cleaned

    @model_validator(mode="after")
    def validate_group_counts(self) -> "ReviewedClusterGroup":
        if len(self.cluster_ids) < 2:
            raise ValueError("reviewed cluster group must include at least two clusters")
        if self.evidence_count < 2:
            raise ValueError("evidence_count must be at least 2")
        if self.source_count < 1:
            raise ValueError("source_count must be at least 1")
        return self
