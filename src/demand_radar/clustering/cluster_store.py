"""JSONL persistence for Stage 2 demand clusters and reviews."""

from __future__ import annotations

from pathlib import Path

from demand_radar.clustering.cluster_review_schema import ClusterReview
from demand_radar.clustering.cluster_schema import DemandCluster
from demand_radar.state.raw_store import next_id, read_jsonl, write_jsonl


DEFAULT_DEMAND_CLUSTERS_PATH = Path("data/processed/demand_clusters.jsonl")
DEFAULT_CLUSTER_REVIEWS_PATH = Path("data/processed/cluster_reviews.jsonl")


def load_demand_clusters(
    path: str | Path = DEFAULT_DEMAND_CLUSTERS_PATH,
) -> list[DemandCluster]:
    return [DemandCluster.model_validate(row) for row in read_jsonl(path)]


def write_demand_clusters(
    clusters: list[DemandCluster],
    path: str | Path = DEFAULT_DEMAND_CLUSTERS_PATH,
) -> int:
    return write_jsonl(path, clusters)


def load_cluster_reviews(
    path: str | Path = DEFAULT_CLUSTER_REVIEWS_PATH,
) -> list[ClusterReview]:
    return [ClusterReview.model_validate(row) for row in read_jsonl(path)]


def append_cluster_review(
    cluster_id: str,
    label: str,
    reviewer_note: str | None = None,
    expected_title_zh: str | None = None,
    should_merge_with: str | None = None,
    should_split: bool | None = None,
    path: str | Path = DEFAULT_CLUSTER_REVIEWS_PATH,
) -> ClusterReview:
    existing = load_cluster_reviews(path)
    review = ClusterReview(
        review_id=next_id("cluster_review", [item.review_id for item in existing]),
        cluster_id=cluster_id,
        label=label,
        reviewer_note=reviewer_note,
        expected_title_zh=expected_title_zh,
        should_merge_with=should_merge_with,
        should_split=should_split,
    )
    write_jsonl(path, [review], append=True)
    return review


def get_latest_cluster_review(
    cluster_id: str,
    reviews: list[ClusterReview] | None = None,
    path: str | Path = DEFAULT_CLUSTER_REVIEWS_PATH,
) -> ClusterReview | None:
    review_list = reviews if reviews is not None else load_cluster_reviews(path)
    matching = [review for review in review_list if review.cluster_id == cluster_id]
    return matching[-1] if matching else None
