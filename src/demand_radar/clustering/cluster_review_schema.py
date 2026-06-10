"""Human review schema for Stage 2 demand clusters."""

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from demand_radar.state.raw_store import utc_now_iso


VALID_CLUSTER_REVIEW_LABELS = {
    "good_cluster",
    "too_broad",
    "too_narrow",
    "wrong_grouping",
    "duplicate_cluster",
    "bad_title",
    "should_merge",
    "should_split",
    "not_a_real_demand",
}


class ClusterReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valid_labels: ClassVar[set[str]] = VALID_CLUSTER_REVIEW_LABELS

    review_id: str = Field(default="")
    cluster_id: str
    label: str
    reviewer_note: str | None = None
    expected_title_zh: str | None = None
    should_merge_with: str | None = None
    should_split: bool | None = None
    created_at: str = Field(default_factory=utc_now_iso)

    @field_validator("review_id")
    @classmethod
    def optional_review_id_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("cluster_id", "label", "created_at")
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
            raise ValueError(f"unsupported cluster review label: {value}")
        return value
