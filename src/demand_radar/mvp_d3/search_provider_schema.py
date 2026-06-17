"""MVP-D3 schema definitions."""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel


class SearchProviderConfig(BaseModel):
    provider_name: str
    api_key_env: str
    enabled: bool = True
    max_results_per_query: int = 5
    timeout_seconds: int = 20


class SearchQuerySelection(BaseModel):
    query_id: str
    seed_id: str
    pain_item_id: str | None = None
    query: str
    query_type: str
    connector: str = "search"
    priority: str = "medium"
    selected_reason_zh: str = ""
    metadata: dict[str, Any] = {}


class SearchResultItem(BaseModel):
    result_id: str
    provider: str
    query_id: str
    seed_id: str
    query: str
    query_type: str
    title: str | None = None
    url: str
    snippet: str | None = None
    published_at: str | None = None
    rank: int = 0
    raw_provider_payload: dict[str, Any] = {}
    created_at: str
    metadata: dict[str, Any] = {}


class MVP_D3_RunSummary(BaseModel):
    generated_at: str
    radar_commit: str = "unknown"
    foundation_commit: str = "b6d23bc"
    provider: str = "none"
    model: str = "none"
    real_llm_run: bool = False
    cache_enabled: bool = True
    provider_available: bool = False
    blocked_reason: str | None = None
    total_v2_queries: int = 0
    selected_queries: int = 0
    total_search_results: int = 0
    unique_urls: int = 0
    evidence_candidates: int = 0
    gate_allowed: int = 0
    gate_blocked: int = 0
    snippet_only_count: int = 0
    full_page_count: int = 0
    selected_for_llm: int = 0
    should_extract_true: int = 0
    strong: int = 0
    medium: int = 0
    weak: int = 0
    failures: int = 0
    cache_hits: int = 0
    yield_rate: float = 0.0
    engineering_acceptance: str = "partial"
    product_acceptance: str = "blocked"
    can_enter_second_review: bool = False
    can_enter_foundation_source_upgrade: bool = False
    reason: str = ""
    errors: list[str] = []