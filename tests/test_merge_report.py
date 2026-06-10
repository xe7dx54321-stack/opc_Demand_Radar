import json
from pathlib import Path

from demand_radar.clustering.cluster_schema import DemandCluster
from demand_radar.clustering.cluster_store import write_demand_clusters
from demand_radar.clustering.merge_report import build_merge_report, build_reviewed_groups_report
from demand_radar.clustering.merge_schema import ClusterMergeCandidate, ReviewedClusterGroup
from demand_radar.clustering.merge_store import (
    append_cluster_group_review,
    write_merge_candidates,
    write_reviewed_cluster_groups,
)


def make_cluster(cluster_id: str) -> DemandCluster:
    return DemandCluster(
        cluster_id=cluster_id,
        cluster_title_zh="投资人在产业跟踪中遇到的「信息分散」问题",
        cluster_summary_zh="投资人在人工智能产业跟踪中遇到信息分散和人工整理低效的问题。",
        personas=["investor"],
        domain_tags=["ai_investment_research"],
        workflow_family="ai_investment_research",
        related_pain_point_ids=[f"pain_{cluster_id[-6:]}"],
        evidence_count=1,
        source_count=1,
        representative_pain_descriptions=["信息分散，人工整理低效"],
        representative_quotes=["证据说明已经转为中文摘要"],
        current_workarounds=["人工表格"],
        cluster_confidence=0.55,
        cluster_method="rule_similarity_v1",
    )


def make_candidate() -> ClusterMergeCandidate:
    return ClusterMergeCandidate(
        merge_candidate_id="merge_candidate_000001",
        cluster_id_a="cluster_000001",
        cluster_id_b="cluster_000002",
        title_a="投资人在产业跟踪中遇到的「信息分散」问题",
        title_b="投资人在产业跟踪中遇到的「人工整理低效」问题",
        similarity_score=78.5,
        strength="strong",
        field_scores={
            "title_similarity": 80.0,
            "summary_similarity": 70.0,
            "pain_description_similarity": 75.0,
            "workaround_similarity": 90.0,
            "persona_similarity": 100.0,
            "domain_similarity": 100.0,
        },
        shared_personas=["investor"],
        shared_domain_tags=["ai_investment_research"],
        shared_keywords=["信息分散"],
        merge_reason_zh="这两个需求主题的核心痛点相似，建议人工检查是否可合并为同一类需求。",
        representative_quotes_a=["证据说明 A"],
        representative_quotes_b=["证据说明 B"],
    )


def test_merge_report_generates_markdown_and_summary(tmp_path: Path) -> None:
    clusters_path = tmp_path / "clusters.jsonl"
    candidates_path = tmp_path / "candidates.jsonl"
    reviews_path = tmp_path / "reviews.jsonl"
    report_path = tmp_path / "cluster_merge_suggestions.md"
    summary_path = tmp_path / "run_summary.json"
    write_demand_clusters([make_cluster("cluster_000001"), make_cluster("cluster_000002")], clusters_path)
    write_merge_candidates([make_candidate()], candidates_path)
    append_cluster_group_review(
        "merge_candidate_000001",
        "cluster_000001",
        "cluster_000002",
        "confirm_merge",
        reviewer_note="人工确认可合并。",
        path=reviews_path,
    )

    summary = build_merge_report(
        clusters_path,
        candidates_path,
        reviews_path,
        report_path,
        summary_path,
    )

    report = report_path.read_text(encoding="utf-8")
    summary_json = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary.merge_candidates == 1
    assert summary.confirmed_merges == 1
    assert "合并建议" in report
    assert "Similarity Score: 78.50" in report
    assert "Latest Review: 确认合并" in report
    assert summary_json["merge_candidates"] == 1


def test_merge_report_ignores_review_when_candidate_pair_changed(tmp_path: Path) -> None:
    clusters_path = tmp_path / "clusters.jsonl"
    candidates_path = tmp_path / "candidates.jsonl"
    reviews_path = tmp_path / "reviews.jsonl"
    report_path = tmp_path / "cluster_merge_suggestions.md"
    summary_path = tmp_path / "run_summary.json"
    write_demand_clusters([make_cluster("cluster_000001"), make_cluster("cluster_000002")], clusters_path)
    write_merge_candidates([make_candidate()], candidates_path)
    append_cluster_group_review(
        "merge_candidate_000001",
        "cluster_000009",
        "cluster_000010",
        "confirm_merge",
        reviewer_note="旧运行里的同 ID 候选，不应贴到当前 pair。",
        path=reviews_path,
    )

    summary = build_merge_report(
        clusters_path,
        candidates_path,
        reviews_path,
        report_path,
        summary_path,
    )

    report = report_path.read_text(encoding="utf-8")
    assert summary.reviewed_candidates == 0
    assert summary.confirmed_merges == 0
    assert "Latest Review: 未审核" in report


def test_reviewed_groups_report_generates_markdown_and_summary(tmp_path: Path) -> None:
    groups_path = tmp_path / "groups.jsonl"
    report_path = tmp_path / "reviewed_cluster_groups_report.md"
    summary_path = tmp_path / "run_summary.json"
    group = ReviewedClusterGroup(
        group_id="cluster_group_000001",
        group_title_zh="投资人在产业跟踪中遇到的信息整理问题",
        group_summary_zh="投资人在产业跟踪中同时遇到信息分散和人工整理低效。",
        cluster_ids=["cluster_000001", "cluster_000002"],
        related_pain_point_ids=["pain_000001", "pain_000002"],
        personas=["investor"],
        domain_tags=["ai_investment_research"],
        evidence_count=2,
        source_count=2,
        representative_pain_descriptions=["信息分散", "人工整理低效"],
        representative_quotes=["证据说明 A", "证据说明 B"],
        current_workarounds=["人工表格"],
        created_from_review_ids=["cluster_group_review_000001"],
    )
    write_reviewed_cluster_groups([group], groups_path)

    summary = build_reviewed_groups_report(groups_path, report_path, summary_path)

    report = report_path.read_text(encoding="utf-8")
    summary_json = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary.reviewed_groups == 1
    assert summary.included_clusters == 2
    assert "投资人在产业跟踪中遇到的信息整理问题" in report
    assert "代表性证据：证据说明 A；证据说明 B" in report
    assert summary_json["reviewed_groups"] == 1
