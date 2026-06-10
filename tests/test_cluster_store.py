from pathlib import Path

from demand_radar.clustering.cluster_schema import DemandCluster
from demand_radar.clustering.cluster_store import (
    append_cluster_review,
    get_latest_cluster_review,
    load_cluster_reviews,
    load_demand_clusters,
    write_demand_clusters,
)


def make_cluster(cluster_id: str = "cluster_000001") -> DemandCluster:
    return DemandCluster(
        cluster_id=cluster_id,
        cluster_title_zh="投资人在产业跟踪中遇到的信息分散问题",
        cluster_summary_zh="投资人在跟踪人工智能产业时反复遇到信息分散和人工整理低效的问题。",
        personas=["investor"],
        domain_tags=["ai_investment_research"],
        workflow_family="ai_investment_research",
        related_pain_point_ids=["pain_000001"],
        evidence_count=1,
        source_count=1,
        representative_pain_descriptions=["信息分散，人工整理低效"],
        representative_quotes=["证据说明已经转为中文摘要"],
        current_workarounds=["人工表格"],
        cluster_confidence=0.55,
        cluster_method="rule_similarity_v1",
    )


def test_demand_clusters_can_be_written_and_loaded(tmp_path: Path) -> None:
    clusters_path = tmp_path / "clusters.jsonl"
    cluster = make_cluster()

    count = write_demand_clusters([cluster], clusters_path)
    loaded = load_demand_clusters(clusters_path)

    assert count == 1
    assert loaded[0].cluster_id == "cluster_000001"
    assert loaded[0].cluster_title_zh == cluster.cluster_title_zh


def test_cluster_reviews_append_and_latest_review_wins(tmp_path: Path) -> None:
    reviews_path = tmp_path / "cluster_reviews.jsonl"

    first = append_cluster_review(
        "cluster_000001",
        "too_broad",
        reviewer_note="主题范围过宽。",
        path=reviews_path,
    )
    second = append_cluster_review(
        "cluster_000001",
        "good_cluster",
        reviewer_note="最新判断为可用主题。",
        path=reviews_path,
    )

    reviews = load_cluster_reviews(reviews_path)
    latest = get_latest_cluster_review("cluster_000001", path=reviews_path)

    assert [review.review_id for review in reviews] == [first.review_id, second.review_id]
    assert latest is not None
    assert latest.label == "good_cluster"
