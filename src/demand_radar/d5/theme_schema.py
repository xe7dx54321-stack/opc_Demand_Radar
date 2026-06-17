"""D5 schema definitions."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


VALID_STRENGTHS = {"strong", "medium", "weak", "mixed", "reject"}
VALID_SOURCE_CATEGORIES = {
    "first_hand_community",
    "workaround_discussion",
    "product_review_comment",
    "practitioner_blog",
    "vendor_blog",
    "content_marketing",
    "job_description",
    "generic_article",
    "technical_issue",
    "unknown",
}
VALID_HUMAN_REVIEW_STATUS = {
    "reviewed_positive",
    "reviewed_reject",
    "reviewed_needs_more_evidence",
    "unreviewed",
    "unknown",
}
VALID_COMMERCIAL = {"high", "medium", "low", "unclear"}
VALID_SOURCE_DIVERSITY = {"high", "medium", "low"}
VALID_ACTIONS = {"pursue_candidate", "watch", "needs_more_evidence", "reject"}
VALID_PRIORITIES = {"high", "medium", "low"}


class DedupedPainItem(BaseModel):
    deduped_item_id: str
    pain_item_id: str
    candidate_id: str | None = None

    title: str | None = None
    source_url: str | None = None
    result_domain: str | None = None
    source_category: str | None = None

    persona: str | None = None
    workflow_stage: str | None = None
    pain_type: str | None = None
    job_to_be_done: str | None = None
    pain_description_zh: str | None = None
    evidence_quote: str | None = None

    evidence_strength: str
    confidence: float

    commercial_signal_type: str | None = None
    current_solution: str | None = None

    raw_text_source: str | None = None
    query_type: str | None = None
    seed_id: str | None = None

    duplicate_group_id: str | None = None
    duplicate_reason: str | None = None
    is_representative: bool = True

    human_review_status: str
    human_action_decision: str | None = None
    human_commercial_potential: str | None = None

    created_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("confidence")
    @classmethod
    def _confidence_range(cls, value: float) -> float:
        if value < 0 or value > 1:
            raise ValueError("confidence must be between 0 and 1")
        return value

    @field_validator("evidence_strength")
    @classmethod
    def _valid_strength(cls, value: str) -> str:
        if value not in VALID_STRENGTHS:
            raise ValueError(f"evidence_strength must be one of {VALID_STRENGTHS}")
        return value

    @field_validator("source_category")
    @classmethod
    def _valid_source_category(cls, value: str | None) -> str | None:
        if value is not None and value not in VALID_SOURCE_CATEGORIES:
            raise ValueError(f"source_category must be one of {VALID_SOURCE_CATEGORIES}")
        return value

    @field_validator("human_review_status")
    @classmethod
    def _valid_human_review_status(cls, value: str) -> str:
        if value not in VALID_HUMAN_REVIEW_STATUS:
            raise ValueError(f"human_review_status must be one of {VALID_HUMAN_REVIEW_STATUS}")
        return value


class SourceEvidenceGroup(BaseModel):
    source_group_id: str
    source_url: str | None = None
    result_domain: str | None = None

    item_ids: list[str] = Field(default_factory=list)
    representative_item_id: str

    source_category: str
    source_weight: float
    group_summary_zh: str

    evidence_count: int
    strong_count: int
    medium_count: int
    weak_count: int

    reviewed_positive_count: int
    reviewed_reject_count: int

    created_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("source_category")
    @classmethod
    def _valid_source_category(cls, value: str) -> str:
        if value not in VALID_SOURCE_CATEGORIES:
            raise ValueError(f"source_category must be one of {VALID_SOURCE_CATEGORIES}")
        return value

    @field_validator("source_weight")
    @classmethod
    def _weight_range(cls, value: float) -> float:
        if value < 0 or value > 1:
            raise ValueError("source_weight must be between 0 and 1")
        return value


class DemandTheme(BaseModel):
    theme_id: str
    theme_title_zh: str

    persona_group: str | None = None
    workflow_group: str | None = None
    pain_type_group: str | None = None

    core_pain_zh: str
    job_to_be_done_zh: str | None = None
    current_workaround_zh: str | None = None

    deduped_item_ids: list[str] = Field(default_factory=list)
    source_group_ids: list[str] = Field(default_factory=list)

    evidence_count: int
    unique_source_url_count: int
    unique_domain_count: int

    strong_count: int
    medium_count: int
    weak_count: int

    first_hand_evidence_count: int
    workaround_evidence_count: int
    marketing_or_vendor_evidence_count: int
    job_description_evidence_count: int

    reviewed_positive_count: int
    reviewed_pursue_count: int
    reviewed_watch_count: int
    reviewed_needs_more_evidence_count: int
    reviewed_reject_count: int

    commercial_potential: str
    evidence_quality: str
    source_diversity: str
    confidence: float

    action_recommendation: str
    recommendation_reason_zh: str

    representative_quotes: list[str] = Field(default_factory=list)
    representative_source_urls: list[str] = Field(default_factory=list)

    created_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("commercial_potential")
    @classmethod
    def _valid_commercial(cls, value: str) -> str:
        if value not in VALID_COMMERCIAL:
            raise ValueError(f"commercial_potential must be one of {VALID_COMMERCIAL}")
        return value

    @field_validator("evidence_quality")
    @classmethod
    def _valid_evidence_quality(cls, value: str) -> str:
        if value not in {"strong", "medium", "weak", "mixed"}:
            raise ValueError("evidence_quality must be strong/medium/weak/mixed")
        return value

    @field_validator("source_diversity")
    @classmethod
    def _valid_source_diversity(cls, value: str) -> str:
        if value not in VALID_SOURCE_DIVERSITY:
            raise ValueError(f"source_diversity must be one of {VALID_SOURCE_DIVERSITY}")
        return value

    @field_validator("confidence")
    @classmethod
    def _confidence_range(cls, value: float) -> float:
        if value < 0 or value > 1:
            raise ValueError("confidence must be between 0 and 1")
        return value

    @field_validator("action_recommendation")
    @classmethod
    def _valid_action(cls, value: str) -> str:
        if value not in VALID_ACTIONS:
            raise ValueError(f"action_recommendation must be one of {VALID_ACTIONS}")
        return value


class ThemeReviewQueueItem(BaseModel):
    queue_item_id: str
    theme_id: str

    theme_title_zh: str
    core_pain_zh: str
    persona_group: str | None = None
    workflow_group: str | None = None

    action_recommendation: str
    commercial_potential: str
    evidence_quality: str
    confidence: float

    evidence_count: int
    unique_domain_count: int
    first_hand_evidence_count: int
    reviewed_pursue_count: int

    representative_quotes: list[str] = Field(default_factory=list)
    representative_source_urls: list[str] = Field(default_factory=list)

    priority: str
    review_reason_zh: str

    created_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("action_recommendation")
    @classmethod
    def _valid_action(cls, value: str) -> str:
        if value not in VALID_ACTIONS:
            raise ValueError(f"action_recommendation must be one of {VALID_ACTIONS}")
        return value

    @field_validator("commercial_potential")
    @classmethod
    def _valid_commercial(cls, value: str) -> str:
        if value not in VALID_COMMERCIAL:
            raise ValueError(f"commercial_potential must be one of {VALID_COMMERCIAL}")
        return value

    @field_validator("priority")
    @classmethod
    def _valid_priority(cls, value: str) -> str:
        if value not in VALID_PRIORITIES:
            raise ValueError(f"priority must be one of {VALID_PRIORITIES}")
        return value


class D5RunSummary(BaseModel):
    domain_id: str
    generated_at: str
    radar_commit: str
    input_pain_items_path: str
    input_reviews_path: str

    total_d4_pain_items: int
    should_extract_true: int
    strong: int
    medium: int
    weak: int
    reviewed_count: int
    reviewed_pursue: int
    reviewed_needs_more_evidence: int
    reviewed_reject: int

    original_items: int
    deduped_representatives: int
    duplicate_groups: int
    theme_count: int
    queue_count: int

    engineering_acceptance: str
    product_acceptance: str
    can_enter_theme_review: bool
    can_enter_product_discovery: bool
    reason: str
    metadata: dict[str, Any] = Field(default_factory=dict)

