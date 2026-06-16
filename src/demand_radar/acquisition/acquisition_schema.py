"""Demand Radar MVP-A: Acquisition schema."""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel


class EvidenceCandidate(BaseModel):
    candidate_id: str

    raw_signal_id: str
    source_id: str
    source_type: str
    source_name: str | None = None
    source_url: str | None = None
    title: str | None = None
    raw_text: str

    domain_id: str
    domain_title_zh: str

    collection_query: str | None = None
    fetched_at: str | None = None

    source_weight: float
    validation_status: str
    # valid | warning | invalid | duplicate

    validation_reasons: list[str] = []
    detected_signal_types: list[str] = []

    include_in_evidence_pack: bool = False

    metadata: dict[str, Any] = {}


class AcquisitionRunSummary(BaseModel):
    run_id: str
    domain_id: str
    started_at: str
    ended_at: str | None = None

    raw_signal_count: int = 0
    unique_signal_count: int = 0
    duplicate_count: int = 0

    evidence_candidate_count: int = 0
    valid_candidate_count: int = 0
    warning_candidate_count: int = 0
    invalid_candidate_count: int = 0

    by_source: dict[str, int] = {}
    by_source_type: dict[str, int] = {}

    errors: list[str] = []
    warnings: list[str] = []
