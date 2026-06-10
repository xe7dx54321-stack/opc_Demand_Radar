"""JSONL persistence and group building for Stage 2.5 merge reviews."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from pydantic import ValidationError

from demand_radar.clustering.cluster_schema import DemandCluster
from demand_radar.clustering.cluster_store import load_demand_clusters
from demand_radar.clustering.merge_schema import (
    ClusterGroupReview,
    ClusterMergeCandidate,
    ReviewedClusterGroup,
)
from demand_radar.state.raw_store import next_id, next_ids, read_jsonl, write_jsonl


DEFAULT_MERGE_CANDIDATES_PATH = Path("data/processed/cluster_merge_candidates.jsonl")
DEFAULT_CLUSTER_GROUP_REVIEWS_PATH = Path("data/processed/cluster_group_reviews.jsonl")
DEFAULT_REVIEWED_CLUSTER_GROUPS_PATH = Path("data/processed/reviewed_cluster_groups.jsonl")


def load_merge_candidates(
    path: str | Path = DEFAULT_MERGE_CANDIDATES_PATH,
) -> list[ClusterMergeCandidate]:
    return [ClusterMergeCandidate.model_validate(row) for row in read_jsonl(path)]


def write_merge_candidates(
    candidates: Iterable[ClusterMergeCandidate],
    path: str | Path = DEFAULT_MERGE_CANDIDATES_PATH,
) -> int:
    return write_jsonl(path, candidates)


def load_cluster_group_reviews(
    path: str | Path = DEFAULT_CLUSTER_GROUP_REVIEWS_PATH,
) -> list[ClusterGroupReview]:
    return [ClusterGroupReview.model_validate(row) for row in read_jsonl(path)]


def append_cluster_group_review(
    merge_candidate_id: str,
    cluster_id_a: str,
    cluster_id_b: str,
    label: str,
    reviewer_note: str | None = None,
    expected_group_title_zh: str | None = None,
    expected_group_summary_zh: str | None = None,
    path: str | Path = DEFAULT_CLUSTER_GROUP_REVIEWS_PATH,
) -> ClusterGroupReview:
    existing = load_cluster_group_reviews(path)
    review = ClusterGroupReview(
        review_id=next_id("cluster_group_review", [item.review_id for item in existing]),
        merge_candidate_id=merge_candidate_id,
        cluster_id_a=cluster_id_a,
        cluster_id_b=cluster_id_b,
        label=label,
        reviewer_note=reviewer_note,
        expected_group_title_zh=expected_group_title_zh,
        expected_group_summary_zh=expected_group_summary_zh,
    )
    write_jsonl(path, [review], append=True)
    return review


def get_latest_review_for_candidate(
    merge_candidate_id: str,
    reviews: list[ClusterGroupReview] | None = None,
    path: str | Path = DEFAULT_CLUSTER_GROUP_REVIEWS_PATH,
    cluster_id_a: str | None = None,
    cluster_id_b: str | None = None,
) -> ClusterGroupReview | None:
    review_list = reviews if reviews is not None else load_cluster_group_reviews(path)
    matching = [review for review in review_list if review.merge_candidate_id == merge_candidate_id]
    if cluster_id_a and cluster_id_b:
        expected_pair = {cluster_id_a, cluster_id_b}
        matching = [
            review
            for review in matching
            if {review.cluster_id_a, review.cluster_id_b} == expected_pair
        ]
    return matching[-1] if matching else None


def build_reviewed_cluster_groups(
    clusters_path: str | Path = "data/processed/demand_clusters.jsonl",
    candidates_path: str | Path = DEFAULT_MERGE_CANDIDATES_PATH,
    reviews_path: str | Path = DEFAULT_CLUSTER_GROUP_REVIEWS_PATH,
    groups_path: str | Path = DEFAULT_REVIEWED_CLUSTER_GROUPS_PATH,
    invalid_groups_path: str | Path = "data/quarantine/invalid_reviewed_groups.jsonl",
) -> list[ReviewedClusterGroup]:
    clusters = load_demand_clusters(clusters_path)
    candidates = load_merge_candidates(candidates_path)
    reviews = load_cluster_group_reviews(reviews_path)
    groups = _build_groups_from_confirmed_reviews(clusters, candidates, reviews)
    valid_groups: list[ReviewedClusterGroup] = []
    invalid_rows: list[dict[str, object]] = []

    for group in groups:
        try:
            validated = ReviewedClusterGroup.model_validate(group.model_dump(mode="json"))
        except (ValidationError, ValueError) as exc:
            invalid_rows.append({"reason": "reviewed_group_invalid", "errors": str(exc), "group": group.model_dump(mode="json")})
            continue
        if not reviewed_cluster_group_gate(validated):
            invalid_rows.append(
                {
                    "reason": "reviewed_group_gate_failed",
                    "group": validated.model_dump(mode="json"),
                }
            )
            continue
        valid_groups.append(validated)

    write_reviewed_cluster_groups(valid_groups, groups_path)
    write_jsonl(invalid_groups_path, invalid_rows)
    return valid_groups


def write_reviewed_cluster_groups(
    groups: Iterable[ReviewedClusterGroup],
    path: str | Path = DEFAULT_REVIEWED_CLUSTER_GROUPS_PATH,
) -> int:
    return write_jsonl(path, groups)


def load_reviewed_cluster_groups(
    path: str | Path = DEFAULT_REVIEWED_CLUSTER_GROUPS_PATH,
) -> list[ReviewedClusterGroup]:
    return [ReviewedClusterGroup.model_validate(row) for row in read_jsonl(path)]


def reviewed_cluster_group_gate(group: ReviewedClusterGroup) -> bool:
    return (
        len(group.cluster_ids) >= 2
        and bool(group.related_pain_point_ids)
        and bool(group.group_title_zh.strip())
        and bool(group.group_summary_zh.strip())
        and group.evidence_count >= 2
    )


def _build_groups_from_confirmed_reviews(
    clusters: list[DemandCluster],
    candidates: list[ClusterMergeCandidate],
    reviews: list[ClusterGroupReview],
) -> list[ReviewedClusterGroup]:
    latest_reviews = {
        candidate.merge_candidate_id: get_latest_review_for_candidate(
            candidate.merge_candidate_id,
            reviews,
            cluster_id_a=candidate.cluster_id_a,
            cluster_id_b=candidate.cluster_id_b,
        )
        for candidate in candidates
    }
    confirmed = [review for review in latest_reviews.values() if review is not None and review.label == "confirm_merge"]
    if not confirmed:
        return []

    cluster_by_id = {cluster.cluster_id: cluster for cluster in clusters}
    parent: dict[str, str] = {}

    def find(cluster_id: str) -> str:
        parent.setdefault(cluster_id, cluster_id)
        while parent[cluster_id] != cluster_id:
            parent[cluster_id] = parent[parent[cluster_id]]
            cluster_id = parent[cluster_id]
        return cluster_id

    def union(left: str, right: str) -> None:
        root_left = find(left)
        root_right = find(right)
        if root_left != root_right:
            parent[root_right] = root_left

    for review in confirmed:
        if review.cluster_id_a in cluster_by_id and review.cluster_id_b in cluster_by_id:
            union(review.cluster_id_a, review.cluster_id_b)

    component_ids: dict[str, list[str]] = {}
    for cluster_id in parent:
        component_ids.setdefault(find(cluster_id), []).append(cluster_id)

    group_ids = next_ids("cluster_group", [], len(component_ids))
    groups: list[ReviewedClusterGroup] = []
    for group_id, cluster_ids in zip(group_ids, component_ids.values(), strict=True):
        component_clusters = [cluster_by_id[cluster_id] for cluster_id in sorted(cluster_ids)]
        component_reviews = [
            review
            for review in confirmed
            if review.cluster_id_a in cluster_ids and review.cluster_id_b in cluster_ids
        ]
        groups.append(_build_group(group_id, component_clusters, component_reviews))
    return groups


def _build_group(
    group_id: str,
    clusters: list[DemandCluster],
    reviews: list[ClusterGroupReview],
) -> ReviewedClusterGroup:
    latest_title = _latest_expected(reviews, "expected_group_title_zh")
    latest_summary = _latest_expected(reviews, "expected_group_summary_zh")
    title_source = max(clusters, key=lambda cluster: (cluster.evidence_count, cluster.cluster_title_zh))
    return ReviewedClusterGroup(
        group_id=group_id,
        group_title_zh=latest_title or title_source.cluster_title_zh,
        group_summary_zh=latest_summary or _truncate(" ".join(_unique(cluster.cluster_summary_zh for cluster in clusters)), 300),
        cluster_ids=_unique(cluster.cluster_id for cluster in clusters),
        related_pain_point_ids=_unique(
            pain_id for cluster in clusters for pain_id in cluster.related_pain_point_ids
        ),
        personas=_unique(persona for cluster in clusters for persona in cluster.personas),
        domain_tags=_unique(tag for cluster in clusters for tag in cluster.domain_tags),
        batch_ids=_unique(batch_id for cluster in clusters for batch_id in cluster.batch_ids),
        evidence_count=sum(cluster.evidence_count for cluster in clusters),
        source_count=sum(cluster.source_count for cluster in clusters),
        representative_pain_descriptions=_unique(
            item for cluster in clusters for item in cluster.representative_pain_descriptions
        )[:5],
        representative_quotes=_unique(item for cluster in clusters for item in cluster.representative_quotes)[:5],
        current_workarounds=_unique(item for cluster in clusters for item in cluster.current_workarounds)[:5],
        created_from_review_ids=_unique(review.review_id for review in reviews),
    )


def _latest_expected(reviews: list[ClusterGroupReview], field_name: str) -> str:
    for review in reversed(reviews):
        value = getattr(review, field_name)
        if value:
            return value
    return ""


def _unique(values: Iterable[str | None]) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in result:
            result.append(text)
    return result


def _truncate(text: str, max_chars: int) -> str:
    text = text.strip()
    return text if len(text) <= max_chars else text[: max_chars - 1] + "…"
