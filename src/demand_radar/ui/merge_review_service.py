"""Service layer for Stage 2.5 merge suggestion review UI."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from pydantic import BaseModel, Field

from demand_radar.clustering.cluster_store import load_demand_clusters
from demand_radar.clustering.merge_schema import (
    VALID_CLUSTER_GROUP_REVIEW_LABELS,
    ClusterGroupReview,
)
from demand_radar.clustering.merge_store import (
    append_cluster_group_review,
    get_latest_review_for_candidate,
    load_cluster_group_reviews,
    load_merge_candidates,
    load_reviewed_cluster_groups,
)


class MergeReviewItem(BaseModel):
    merge_candidate_id: str
    cluster_id_a: str
    cluster_id_b: str
    title_a: str
    title_b: str
    similarity_score: float
    strength: str
    field_scores: dict[str, float] = Field(default_factory=dict)
    shared_personas: list[str] = Field(default_factory=list)
    shared_domain_tags: list[str] = Field(default_factory=list)
    shared_keywords: list[str] = Field(default_factory=list)
    batch_ids: list[str] = Field(default_factory=list)
    merge_reason_zh: str
    risk_note_zh: str | None = None
    representative_quotes_a: list[str] = Field(default_factory=list)
    representative_quotes_b: list[str] = Field(default_factory=list)
    latest_review_label: str | None = None
    latest_review_note: str | None = None
    latest_review_id: str | None = None
    reviewed: bool = False


class MergeReviewSummary(BaseModel):
    demand_clusters: int
    merge_candidates: int
    strong_candidates: int
    medium_candidates: int
    reviewed_candidates: int
    confirmed_merges: int
    rejected_merges: int
    maybe_merges: int
    reviewed_groups: int
    labels: dict[str, int] = Field(default_factory=dict)


def load_merge_review_items(
    candidates_path: str | Path = "data/processed/cluster_merge_candidates.jsonl",
    reviews_path: str | Path = "data/processed/cluster_group_reviews.jsonl",
) -> list[MergeReviewItem]:
    candidates = load_merge_candidates(candidates_path)
    reviews = load_cluster_group_reviews(reviews_path)
    items: list[MergeReviewItem] = []
    for candidate in candidates:
        latest = get_latest_review_for_candidate(
            candidate.merge_candidate_id,
            reviews,
            cluster_id_a=candidate.cluster_id_a,
            cluster_id_b=candidate.cluster_id_b,
        )
        payload = candidate.model_dump(mode="json")
        payload.update(
            {
                "latest_review_label": latest.label if latest else None,
                "latest_review_note": latest.reviewer_note if latest else None,
                "latest_review_id": latest.review_id if latest else None,
                "reviewed": latest is not None,
            }
        )
        items.append(MergeReviewItem.model_validate(payload))
    return items


def get_merge_review_summary(
    items: list[MergeReviewItem],
    clusters_path: str | Path = "data/processed/demand_clusters.jsonl",
    reviews_path: str | Path = "data/processed/cluster_group_reviews.jsonl",
    groups_path: str | Path = "data/processed/reviewed_cluster_groups.jsonl",
) -> MergeReviewSummary:
    reviews = load_cluster_group_reviews(reviews_path)
    groups = load_reviewed_cluster_groups(groups_path)
    latest_labels = [item.latest_review_label for item in items if item.latest_review_label]
    label_counts = Counter(latest_labels)
    labels = {label: label_counts[label] for label in sorted(VALID_CLUSTER_GROUP_REVIEW_LABELS)}
    return MergeReviewSummary(
        demand_clusters=len(load_demand_clusters(clusters_path)),
        merge_candidates=len(items),
        strong_candidates=sum(1 for item in items if item.strength == "strong"),
        medium_candidates=sum(1 for item in items if item.strength == "medium"),
        reviewed_candidates=sum(1 for item in items if item.reviewed),
        confirmed_merges=label_counts["confirm_merge"],
        rejected_merges=label_counts["reject_merge"] + label_counts["not_same_demand"],
        maybe_merges=label_counts["maybe_merge"],
        reviewed_groups=len(groups),
        labels=labels,
    )


def add_merge_review(
    item: MergeReviewItem,
    label: str,
    reviewer_note: str | None = None,
    expected_group_title_zh: str | None = None,
    expected_group_summary_zh: str | None = None,
    reviews_path: str | Path = "data/processed/cluster_group_reviews.jsonl",
) -> ClusterGroupReview:
    return append_cluster_group_review(
        merge_candidate_id=item.merge_candidate_id,
        cluster_id_a=item.cluster_id_a,
        cluster_id_b=item.cluster_id_b,
        label=label,
        reviewer_note=reviewer_note,
        expected_group_title_zh=expected_group_title_zh or None,
        expected_group_summary_zh=expected_group_summary_zh or None,
        path=reviews_path,
    )


def get_available_merge_batches(items: list[MergeReviewItem]) -> list[str]:
    batches = {batch_id for item in items for batch_id in _item_batches(item)}
    return sorted(batches)


def filter_merge_items_by_batch(
    items: list[MergeReviewItem],
    batch_id: str,
) -> list[MergeReviewItem]:
    if batch_id == "All":
        return items
    return [item for item in items if batch_id in _item_batches(item)]


def _item_batches(item: MergeReviewItem) -> list[str]:
    return [batch_id for batch_id in item.batch_ids if batch_id] or ["default"]
