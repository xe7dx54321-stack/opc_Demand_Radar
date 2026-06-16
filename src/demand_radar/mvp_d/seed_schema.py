"""MVP-D seed schema definitions."""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field, field_validator


class ReviewedPainSeed(BaseModel):
    seed_id: str
    pain_item_id: str
    candidate_id: str

    title: str | None = None
    source_url: str
    source_type: str | None = None

    persona: str | None = None
    workflow_stage: str | None = None
    pain_type: str | None = None
    pain_description_zh: str | None = None
    evidence_quote: str | None = None

    true_pain: bool
    commercial_potential: str | None = None
    evidence_quality: str | None = None
    action_decision: str | None = None

    expansion_priority: str  # high | medium | low

    seed_reason_zh: str
    created_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("expansion_priority")
    @classmethod
    def _valid_priority(cls, v: str) -> str:
        if v not in {"high", "medium", "low"}:
            raise ValueError(f"expansion_priority must be high/medium/low, got {v!r}")
        return v


class SeededQuery(BaseModel):
    query_id: str
    seed_id: str
    pain_item_id: str

    connector: str
    query: str
    query_type: str
    # persona_workflow | pain_expression | competitor_alternative | problem_phrase | workaround_phrase

    expected_signal_type: str
    # pain | workaround | paid_signal | workflow | complaint | comparison

    priority: str  # high | medium | low
    negative_terms: list[str] = Field(default_factory=list)
    created_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceTheme(BaseModel):
    theme_id: str
    theme_title_zh: str

    seed_ids: list[str] = Field(default_factory=list)
    pain_item_ids: list[str] = Field(default_factory=list)
    evidence_candidate_ids: list[str] = Field(default_factory=list)

    persona_group: str | None = None
    workflow_group: str | None = None
    pain_type_group: str | None = None

    theme_summary_zh: str
    evidence_count: int
    reviewed_seed_count: int
    new_evidence_count: int

    commercial_potential: str  # high | medium | low | unclear
    confidence: float
    action_recommendation: str
    # pursue_candidate | watch | needs_more_evidence | reject

    representative_quotes: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)

    created_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class SeedConsolidation(BaseModel):
    consolidation_id: str
    seed_id: str
    pain_item_id: str

    original_title: str | None = None
    new_related_candidates_count: int
    new_extracted_pain_count: int
    strong_evidence_count: int
    medium_evidence_count: int
    weak_evidence_count: int
    commercial_signal_count: int
    source_url_count: int
    recommendation: str
    # pursue_candidate | watch | needs_more_evidence | reject

    recommendation_reason_zh: str
    created_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class MVPDRunSummary(BaseModel):
    domain_id: str
    generated_at: str
    total_reviews: int = 0
    eligible_seeds: int = 0
    optional_seeds: int = 0
    excluded_reviews: int = 0
    total_queries: int = 0
    raw_new_signals: int = 0
    unique_new_signals: int = 0
    deduped_against_existing: int = 0
    allowed_by_gate: int = 0
    blocked_by_gate: int = 0
    selected_for_llm: int = 0
    expansion_pain_items: int = 0
    should_extract_true: int = 0
    themes: int = 0
    engineering_acceptance: str
    product_acceptance: str
    can_enter_second_review: bool
    can_enter_product_discovery: bool
    reason: str
    metadata: dict[str, Any] = Field(default_factory=dict)
