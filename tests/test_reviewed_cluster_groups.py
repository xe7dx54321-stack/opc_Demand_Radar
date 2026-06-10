from pathlib import Path

from demand_radar.clustering.cluster_schema import DemandCluster
from demand_radar.clustering.cluster_store import write_demand_clusters
from demand_radar.clustering.merge_schema import ClusterMergeCandidate
from demand_radar.clustering.merge_store import (
    append_cluster_group_review,
    build_reviewed_cluster_groups,
    load_reviewed_cluster_groups,
    write_merge_candidates,
)
from demand_radar.state.raw_store import read_jsonl


def make_cluster(cluster_id: str, title_suffix: str) -> DemandCluster:
    return DemandCluster(
        cluster_id=cluster_id,
        cluster_title_zh=f"投资人在产业跟踪中遇到的「{title_suffix}」问题",
        cluster_summary_zh=f"投资人在人工智能产业跟踪中遇到{title_suffix}的问题。",
        personas=["investor"],
        domain_tags=["ai_investment_research"],
        workflow_family="ai_investment_research",
        related_pain_point_ids=[f"pain_{cluster_id[-6:]}"],
        evidence_count=1,
        source_count=1,
        representative_pain_descriptions=[title_suffix],
        representative_quotes=[f"{title_suffix}的中文证据说明"],
        current_workarounds=["人工表格"],
        cluster_confidence=0.55,
        cluster_method="rule_similarity_v1",
    )


def make_candidate(candidate_id: str, cluster_id_a: str, cluster_id_b: str) -> ClusterMergeCandidate:
    return ClusterMergeCandidate(
        merge_candidate_id=candidate_id,
        cluster_id_a=cluster_id_a,
        cluster_id_b=cluster_id_b,
        title_a=f"{cluster_id_a} 中文标题",
        title_b=f"{cluster_id_b} 中文标题",
        similarity_score=80,
        strength="strong",
        field_scores={"title_similarity": 80.0},
        shared_personas=["investor"],
        shared_domain_tags=["ai_investment_research"],
        shared_keywords=["信息分散"],
        merge_reason_zh="这两个需求主题的核心痛点相似，建议人工检查是否可合并为同一类需求。",
        representative_quotes_a=["证据说明 A"],
        representative_quotes_b=["证据说明 B"],
    )


def test_confirm_merge_builds_reviewed_group(tmp_path: Path) -> None:
    clusters_path = tmp_path / "clusters.jsonl"
    candidates_path = tmp_path / "candidates.jsonl"
    reviews_path = tmp_path / "reviews.jsonl"
    groups_path = tmp_path / "groups.jsonl"
    invalid_path = tmp_path / "invalid_groups.jsonl"
    write_demand_clusters(
        [
            make_cluster("cluster_000001", "信息分散"),
            make_cluster("cluster_000002", "人工整理低效"),
        ],
        clusters_path,
    )
    write_merge_candidates(
        [make_candidate("merge_candidate_000001", "cluster_000001", "cluster_000002")],
        candidates_path,
    )
    review = append_cluster_group_review(
        "merge_candidate_000001",
        "cluster_000001",
        "cluster_000002",
        "confirm_merge",
        expected_group_title_zh="投资人在产业跟踪中遇到的信息整理问题",
        expected_group_summary_zh="投资人在产业跟踪中同时遇到信息分散和人工整理低效。",
        path=reviews_path,
    )

    groups = build_reviewed_cluster_groups(
        clusters_path,
        candidates_path,
        reviews_path,
        groups_path,
        invalid_path,
    )

    assert len(groups) == 1
    assert groups[0].cluster_ids == ["cluster_000001", "cluster_000002"]
    assert groups[0].group_title_zh == "投资人在产业跟踪中遇到的信息整理问题"
    assert groups[0].created_from_review_ids == [review.review_id]
    assert load_reviewed_cluster_groups(groups_path)[0].group_id == "cluster_group_000001"
    assert read_jsonl(invalid_path) == []


def test_reject_merge_does_not_build_reviewed_group(tmp_path: Path) -> None:
    clusters_path = tmp_path / "clusters.jsonl"
    candidates_path = tmp_path / "candidates.jsonl"
    reviews_path = tmp_path / "reviews.jsonl"
    groups_path = tmp_path / "groups.jsonl"
    invalid_path = tmp_path / "invalid_groups.jsonl"
    write_demand_clusters(
        [
            make_cluster("cluster_000001", "信息分散"),
            make_cluster("cluster_000002", "人工整理低效"),
        ],
        clusters_path,
    )
    write_merge_candidates(
        [make_candidate("merge_candidate_000001", "cluster_000001", "cluster_000002")],
        candidates_path,
    )
    append_cluster_group_review(
        "merge_candidate_000001",
        "cluster_000001",
        "cluster_000002",
        "reject_merge",
        path=reviews_path,
    )

    groups = build_reviewed_cluster_groups(
        clusters_path,
        candidates_path,
        reviews_path,
        groups_path,
        invalid_path,
    )

    assert groups == []
    assert read_jsonl(groups_path) == []


def test_connected_confirmed_pairs_become_one_group(tmp_path: Path) -> None:
    clusters_path = tmp_path / "clusters.jsonl"
    candidates_path = tmp_path / "candidates.jsonl"
    reviews_path = tmp_path / "reviews.jsonl"
    groups_path = tmp_path / "groups.jsonl"
    invalid_path = tmp_path / "invalid_groups.jsonl"
    write_demand_clusters(
        [
            make_cluster("cluster_000001", "信息分散"),
            make_cluster("cluster_000002", "人工整理低效"),
            make_cluster("cluster_000003", "难验证"),
        ],
        clusters_path,
    )
    write_merge_candidates(
        [
            make_candidate("merge_candidate_000001", "cluster_000001", "cluster_000002"),
            make_candidate("merge_candidate_000002", "cluster_000002", "cluster_000003"),
        ],
        candidates_path,
    )
    append_cluster_group_review(
        "merge_candidate_000001",
        "cluster_000001",
        "cluster_000002",
        "confirm_merge",
        path=reviews_path,
    )
    append_cluster_group_review(
        "merge_candidate_000002",
        "cluster_000002",
        "cluster_000003",
        "confirm_merge",
        path=reviews_path,
    )

    groups = build_reviewed_cluster_groups(
        clusters_path,
        candidates_path,
        reviews_path,
        groups_path,
        invalid_path,
    )

    assert len(groups) == 1
    assert groups[0].cluster_ids == ["cluster_000001", "cluster_000002", "cluster_000003"]
    assert groups[0].evidence_count == 3
    assert groups[0].related_pain_point_ids == ["pain_000001", "pain_000002", "pain_000003"]
