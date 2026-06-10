"""Service layer for Stage 2 demand cluster review UI."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from pydantic import BaseModel, Field

from demand_radar.clustering.cluster_review_schema import VALID_CLUSTER_REVIEW_LABELS, ClusterReview
from demand_radar.clustering.cluster_schema import DemandCluster
from demand_radar.clustering.cluster_store import (
    append_cluster_review,
    get_latest_cluster_review,
    load_cluster_reviews,
    load_demand_clusters,
)


class ClusterReviewItem(BaseModel):
    cluster_id: str
    cluster_title_zh: str
    cluster_summary_zh: str
    personas: list[str] = Field(default_factory=list)
    domain_tags: list[str] = Field(default_factory=list)
    workflow_family: str | None = None
    related_pain_point_ids: list[str] = Field(default_factory=list)
    evidence_count: int
    source_count: int
    representative_pain_descriptions: list[str] = Field(default_factory=list)
    representative_quotes: list[str] = Field(default_factory=list)
    current_workarounds: list[str] = Field(default_factory=list)
    cluster_confidence: float
    cluster_method: str
    latest_review_label: str | None = None
    latest_review_note: str | None = None
    latest_review_id: str | None = None
    reviewed: bool = False


class ClusterReviewSummary(BaseModel):
    demand_clusters: int
    singleton_clusters: int
    reviewed_clusters: int
    unreviewed_clusters: int
    cluster_reviews: int
    labels: dict[str, int] = Field(default_factory=dict)


def load_cluster_review_items(
    clusters_path: str | Path = "data/processed/demand_clusters.jsonl",
    reviews_path: str | Path = "data/processed/cluster_reviews.jsonl",
) -> list[ClusterReviewItem]:
    clusters = load_demand_clusters(clusters_path)
    reviews = load_cluster_reviews(reviews_path)
    return [_item_from_cluster(cluster, reviews) for cluster in clusters]


def get_cluster_review_summary(
    items: list[ClusterReviewItem],
    reviews_path: str | Path = "data/processed/cluster_reviews.jsonl",
) -> ClusterReviewSummary:
    reviews = load_cluster_reviews(reviews_path)
    counts = Counter(item.latest_review_label for item in items if item.latest_review_label)
    labels = {label: counts[label] for label in sorted(VALID_CLUSTER_REVIEW_LABELS)}
    reviewed = sum(1 for item in items if item.reviewed)
    return ClusterReviewSummary(
        demand_clusters=len(items),
        singleton_clusters=sum(1 for item in items if item.evidence_count == 1),
        reviewed_clusters=reviewed,
        unreviewed_clusters=len(items) - reviewed,
        cluster_reviews=len(reviews),
        labels=labels,
    )


def add_cluster_review(
    item: ClusterReviewItem,
    label: str,
    reviewer_note: str | None = None,
    expected_title_zh: str | None = None,
    should_merge_with: str | None = None,
    should_split: bool | None = None,
    reviews_path: str | Path = "data/processed/cluster_reviews.jsonl",
) -> ClusterReview:
    return append_cluster_review(
        cluster_id=item.cluster_id,
        label=label,
        reviewer_note=reviewer_note,
        expected_title_zh=expected_title_zh or None,
        should_merge_with=should_merge_with or None,
        should_split=should_split,
        path=reviews_path,
    )


def _item_from_cluster(cluster: DemandCluster, reviews: list[ClusterReview]) -> ClusterReviewItem:
    latest = get_latest_cluster_review(cluster.cluster_id, reviews=reviews)
    payload = cluster.model_dump(mode="json")
    payload.update(
        {
            "latest_review_label": latest.label if latest else None,
            "latest_review_note": latest.reviewer_note if latest else None,
            "latest_review_id": latest.review_id if latest else None,
            "reviewed": latest is not None,
        }
    )
    return ClusterReviewItem.model_validate(payload)
