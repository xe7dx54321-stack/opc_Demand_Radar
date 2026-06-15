"""Tests for AI reviewed cluster groups building."""
from __future__ import annotations

from pathlib import Path

from demand_radar.clustering.cluster_schema import DemandCluster
from demand_radar.clustering.cluster_store import write_demand_clusters
from demand_radar.semantic_merge.semantic_merge_schema import AIReviewedClusterGroup, SemanticMergeJudgment
from demand_radar.semantic_merge.semantic_merge_store import (
    build_ai_reviewed_cluster_groups,
    load_ai_reviewed_cluster_groups,
    write_ai_reviewed_cluster_groups,
    write_semantic_merge_judgments,
)


def _make_cluster(cluster_id: str, pain_ids: list[str]) -> DemandCluster:
    return DemandCluster(
        cluster_id=cluster_id,
        cluster_title_zh=f"需求主题{cluster_id}",
        cluster_summary_zh=f"需求主题{cluster_id}摘要内容",
        personas=["investor"],
        domain_tags=["ai_investment_research"],
        workflow_family="ai_investment_research",
        related_pain_point_ids=pain_ids,
        evidence_count=len(pain_ids),
        source_count=1,
        representative_pain_descriptions=["信息分散，人工整理效率低"],
        representative_quotes=["示例引用文本"],
        current_workarounds=["人工表格整理"],
        cluster_confidence=0.65,
        cluster_method="rule_similarity_v1",
    )


def _make_confirm_judgment(j_id: str, ca: str, cb: str) -> SemanticMergeJudgment:
    return SemanticMergeJudgment(
        judgment_id=j_id,
        merge_candidate_id=f"mc_{j_id}",
        cluster_id_a=ca,
        cluster_id_b=cb,
        decision="confirm_merge",
        confidence=0.92,
        reason_zh="两个主题核心痛点高度一致，建议合并。",
        suggested_group_title_zh="AI 产业研究中遇到的信息分散问题",
        suggested_group_summary_zh="两个需求均涉及信息分散导致的人工整理效率低问题。",
        auto_action="auto_confirm",
        judge_mode="rule_based_stub",
    )


def test_ai_group_requires_at_least_two_clusters(tmp_path: Path):
    clusters = [_make_cluster("ca001", ["p001"]), _make_cluster("cb001", ["p002"])]
    clusters_path = tmp_path / "clusters.jsonl"
    write_demand_clusters(clusters, clusters_path)

    j = _make_confirm_judgment("j001", "ca001", "cb001")
    judgments_path = tmp_path / "judgments.jsonl"
    write_semantic_merge_judgments([j], judgments_path)

    groups = build_ai_reviewed_cluster_groups(
        clusters_path=clusters_path,
        judgments_path=judgments_path,
        groups_path=tmp_path / "groups.jsonl",
        invalid_groups_path=tmp_path / "invalid.jsonl",
    )
    assert len(groups) == 1
    assert len(groups[0].cluster_ids) >= 2


def test_ai_group_aggregates_pain_point_ids(tmp_path: Path):
    clusters = [_make_cluster("ca001", ["p001", "p002"]), _make_cluster("cb001", ["p003"])]
    clusters_path = tmp_path / "clusters.jsonl"
    write_demand_clusters(clusters, clusters_path)

    j = _make_confirm_judgment("j001", "ca001", "cb001")
    judgments_path = tmp_path / "judgments.jsonl"
    write_semantic_merge_judgments([j], judgments_path)

    groups = build_ai_reviewed_cluster_groups(
        clusters_path=clusters_path,
        judgments_path=judgments_path,
        groups_path=tmp_path / "groups.jsonl",
        invalid_groups_path=tmp_path / "invalid.jsonl",
    )
    assert "p001" in groups[0].related_pain_point_ids
    assert "p003" in groups[0].related_pain_point_ids


def test_abc_connected_components(tmp_path: Path):
    clusters = [
        _make_cluster("a001", ["p001"]),
        _make_cluster("b001", ["p002"]),
        _make_cluster("c001", ["p003"]),
    ]
    clusters_path = tmp_path / "clusters.jsonl"
    write_demand_clusters(clusters, clusters_path)

    judgments_path = tmp_path / "judgments.jsonl"
    write_semantic_merge_judgments(
        [
            _make_confirm_judgment("j001", "a001", "b001"),
            _make_confirm_judgment("j002", "b001", "c001"),
        ],
        judgments_path,
    )

    groups = build_ai_reviewed_cluster_groups(
        clusters_path=clusters_path,
        judgments_path=judgments_path,
        groups_path=tmp_path / "groups.jsonl",
        invalid_groups_path=tmp_path / "invalid.jsonl",
    )
    assert len(groups) == 1
    assert set(groups[0].cluster_ids) == {"a001", "b001", "c001"}


def test_two_disconnected_pairs_become_two_groups(tmp_path: Path):
    clusters = [
        _make_cluster("a001", ["p001"]),
        _make_cluster("b001", ["p002"]),
        _make_cluster("c001", ["p003"]),
        _make_cluster("d001", ["p004"]),
    ]
    clusters_path = tmp_path / "clusters.jsonl"
    write_demand_clusters(clusters, clusters_path)

    judgments_path = tmp_path / "judgments.jsonl"
    write_semantic_merge_judgments(
        [
            _make_confirm_judgment("j001", "a001", "b001"),
            _make_confirm_judgment("j002", "c001", "d001"),
        ],
        judgments_path,
    )

    groups = build_ai_reviewed_cluster_groups(
        clusters_path=clusters_path,
        judgments_path=judgments_path,
        groups_path=tmp_path / "groups.jsonl",
        invalid_groups_path=tmp_path / "invalid.jsonl",
    )
    assert len(groups) == 2
    all_clusters = {cid for group in groups for cid in group.cluster_ids}
    assert all_clusters == {"a001", "b001", "c001", "d001"}


def test_ai_group_write_and_load_roundtrip(tmp_path: Path):
    group = AIReviewedClusterGroup(
        group_id="g001",
        group_title_zh="测试需求组标题",
        group_summary_zh="测试需求组摘要内容",
        cluster_ids=["ca001", "cb001"],
        related_pain_point_ids=["p001", "p002"],
        evidence_count=2,
        source_count=1,
        created_from_judgment_ids=["j001"],
    )
    path = tmp_path / "groups.jsonl"
    write_ai_reviewed_cluster_groups([group], path)
    loaded = load_ai_reviewed_cluster_groups(path)
    assert len(loaded) == 1
    assert loaded[0].group_id == "g001"
    assert loaded[0].created_by == "ai_semantic_merge"
