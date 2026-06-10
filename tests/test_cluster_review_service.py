from pathlib import Path

from demand_radar.clustering.cluster_store import write_demand_clusters
from demand_radar.clustering.cluster_schema import DemandCluster
from demand_radar.ui.cluster_review_service import (
    add_cluster_review,
    get_cluster_review_summary,
    load_cluster_review_items,
)


def make_cluster(
    cluster_id: str,
    evidence_count: int = 1,
    related_ids: list[str] | None = None,
) -> DemandCluster:
    related = related_ids or [f"pain_{cluster_id[-6:]}"]
    return DemandCluster(
        cluster_id=cluster_id,
        cluster_title_zh="投资人在产业跟踪中遇到的信息分散问题",
        cluster_summary_zh="投资人在跟踪人工智能产业时反复遇到信息分散和人工整理低效的问题。",
        personas=["investor"],
        domain_tags=["ai_investment_research"],
        workflow_family="ai_investment_research",
        related_pain_point_ids=related,
        evidence_count=evidence_count,
        source_count=1,
        representative_pain_descriptions=["信息分散，人工整理低效"],
        representative_quotes=["证据说明已经转为中文摘要"],
        current_workarounds=["人工表格"],
        cluster_confidence=0.55,
        cluster_method="rule_similarity_v1",
    )


def test_cluster_review_service_loads_items_and_summary(tmp_path: Path) -> None:
    clusters_path = tmp_path / "clusters.jsonl"
    reviews_path = tmp_path / "cluster_reviews.jsonl"
    write_demand_clusters(
        [
            make_cluster("cluster_000001"),
            make_cluster("cluster_000002", evidence_count=2, related_ids=["pain_000002", "pain_000003"]),
        ],
        clusters_path,
    )

    items = load_cluster_review_items(clusters_path, reviews_path)
    review = add_cluster_review(items[0], "good_cluster", "主题可用。", reviews_path=reviews_path)
    refreshed = load_cluster_review_items(clusters_path, reviews_path)
    summary = get_cluster_review_summary(refreshed, reviews_path)

    assert review.review_id == "cluster_review_000001"
    assert len(refreshed) == 2
    assert refreshed[0].reviewed
    assert refreshed[0].latest_review_label == "good_cluster"
    assert summary.demand_clusters == 2
    assert summary.singleton_clusters == 1
    assert summary.reviewed_clusters == 1
    assert summary.unreviewed_clusters == 1
    assert summary.labels["good_cluster"] == 1


def test_cluster_review_service_empty_files_are_safe(tmp_path: Path) -> None:
    clusters_path = tmp_path / "clusters.jsonl"
    reviews_path = tmp_path / "cluster_reviews.jsonl"

    items = load_cluster_review_items(clusters_path, reviews_path)
    summary = get_cluster_review_summary(items, reviews_path)

    assert items == []
    assert summary.demand_clusters == 0
    assert summary.unreviewed_clusters == 0
