from pathlib import Path

from demand_radar.clustering.cluster_schema import DemandCluster
from demand_radar.clustering.cluster_store import write_demand_clusters
from demand_radar.clustering.merge_schema import ClusterMergeCandidate, ReviewedClusterGroup
from demand_radar.clustering.merge_store import (
    write_merge_candidates,
    write_reviewed_cluster_groups,
)
from demand_radar.ui.merge_review_service import (
    add_merge_review,
    get_merge_review_summary,
    load_merge_review_items,
)


def make_cluster(cluster_id: str) -> DemandCluster:
    return DemandCluster(
        cluster_id=cluster_id,
        cluster_title_zh="投资人在产业跟踪中遇到的「信息分散」问题",
        cluster_summary_zh="投资人在人工智能产业跟踪中遇到信息分散的问题。",
        personas=["investor"],
        domain_tags=["ai_investment_research"],
        workflow_family="ai_investment_research",
        related_pain_point_ids=[f"pain_{cluster_id[-6:]}"],
        evidence_count=1,
        source_count=1,
        representative_pain_descriptions=["信息分散"],
        representative_quotes=["证据说明已经转为中文摘要"],
        current_workarounds=["人工表格"],
        cluster_confidence=0.55,
        cluster_method="rule_similarity_v1",
    )


def make_candidate(
    candidate_id: str,
    strength: str = "strong",
    score: float = 80.0,
) -> ClusterMergeCandidate:
    return ClusterMergeCandidate(
        merge_candidate_id=candidate_id,
        cluster_id_a="cluster_000001",
        cluster_id_b="cluster_000002",
        title_a="投资人在产业跟踪中遇到的「信息分散」问题",
        title_b="投资人在产业跟踪中遇到的「人工整理低效」问题",
        similarity_score=score,
        strength=strength,
        field_scores={"title_similarity": score},
        shared_personas=["investor"],
        shared_domain_tags=["ai_investment_research"],
        shared_keywords=["信息分散"],
        merge_reason_zh="这两个需求主题的核心痛点相似，建议人工检查是否可合并为同一类需求。",
        representative_quotes_a=["证据说明 A"],
        representative_quotes_b=["证据说明 B"],
    )


def test_merge_review_service_loads_items_and_summary(tmp_path: Path) -> None:
    clusters_path = tmp_path / "clusters.jsonl"
    candidates_path = tmp_path / "candidates.jsonl"
    reviews_path = tmp_path / "reviews.jsonl"
    groups_path = tmp_path / "groups.jsonl"
    write_demand_clusters([make_cluster("cluster_000001"), make_cluster("cluster_000002")], clusters_path)
    write_merge_candidates(
        [
            make_candidate("merge_candidate_000001", "strong", 80.0),
            make_candidate("merge_candidate_000002", "medium", 68.0),
        ],
        candidates_path,
    )
    group = ReviewedClusterGroup(
        group_id="cluster_group_000001",
        group_title_zh="投资人在产业跟踪中遇到的信息整理问题",
        group_summary_zh="投资人在产业跟踪中同时遇到信息分散和人工整理低效。",
        cluster_ids=["cluster_000001", "cluster_000002"],
        related_pain_point_ids=["pain_000001", "pain_000002"],
        evidence_count=2,
        source_count=2,
    )
    write_reviewed_cluster_groups([group], groups_path)

    items = load_merge_review_items(candidates_path, reviews_path)
    review = add_merge_review(
        items[0],
        "confirm_merge",
        "人工确认可合并。",
        expected_group_title_zh="投资人在产业跟踪中遇到的信息整理问题",
        reviews_path=reviews_path,
    )
    refreshed = load_merge_review_items(candidates_path, reviews_path)
    summary = get_merge_review_summary(refreshed, clusters_path, reviews_path, groups_path)

    assert review.review_id == "cluster_group_review_000001"
    assert len(refreshed) == 2
    assert refreshed[0].reviewed
    assert refreshed[0].latest_review_label == "confirm_merge"
    assert refreshed[0].field_scores["title_similarity"] == 80.0
    assert summary.demand_clusters == 2
    assert summary.merge_candidates == 2
    assert summary.strong_candidates == 1
    assert summary.medium_candidates == 1
    assert summary.confirmed_merges == 1
    assert summary.reviewed_groups == 1


def test_merge_review_service_empty_files_are_safe(tmp_path: Path) -> None:
    clusters_path = tmp_path / "clusters.jsonl"
    candidates_path = tmp_path / "candidates.jsonl"
    reviews_path = tmp_path / "reviews.jsonl"
    groups_path = tmp_path / "groups.jsonl"

    items = load_merge_review_items(candidates_path, reviews_path)
    summary = get_merge_review_summary(items, clusters_path, reviews_path, groups_path)

    assert items == []
    assert summary.demand_clusters == 0
    assert summary.merge_candidates == 0
    assert summary.reviewed_candidates == 0
