"""Schemas for Stage 2.6 batch-level radar summaries."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from demand_radar.state.raw_store import utc_now_iso


class BatchSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    batch_id: str

    raw_signals: int
    normalized_signals: int
    pain_points: int
    quarantined_items: int

    demand_clusters: int
    singleton_clusters: int
    merge_candidates: int
    reviewed_groups: int

    calibration_reviews: int
    cluster_reviews: int
    merge_reviews: int

    extraction_yield: float | None = None
    quarantine_rate: float | None = None
    singleton_rate: float | None = None
    merge_candidate_rate: float | None = None

    good_extractions: int = 0
    weak_extractions: int = 0
    false_positives: int = 0
    bad_quotes: int = 0
    should_quarantine: int = 0

    created_at: str = Field(default_factory=utc_now_iso)


class Stage3Readiness(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sample_size_ok: bool
    pain_volume_ok: bool
    group_volume_ok: bool
    clustering_convergence_ok: bool
    ready_for_truth_scoring: str
    recommendation: str


class BatchSummaryResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    overall: BatchSummary
    batches: list[BatchSummary]
    readiness: Stage3Readiness
    generated_at: str = Field(default_factory=utc_now_iso)
