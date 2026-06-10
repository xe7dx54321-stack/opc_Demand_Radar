from demand_radar.clustering.cluster_schema import DemandCluster
from demand_radar.clustering.merge_similarity import cluster_merge_similarity, shared_keywords


def make_cluster(
    cluster_id: str,
    title: str,
    summary: str,
    persona: str = "investor",
    domain: str = "ai_investment_research",
    pain: str = "信息分散，人工整理低效",
    workaround: str = "人工表格",
) -> DemandCluster:
    return DemandCluster(
        cluster_id=cluster_id,
        cluster_title_zh=title,
        cluster_summary_zh=summary,
        personas=[persona],
        domain_tags=[domain],
        workflow_family=domain,
        related_pain_point_ids=[f"pain_{cluster_id[-6:]}"],
        evidence_count=1,
        source_count=1,
        representative_pain_descriptions=[pain],
        representative_quotes=["证据说明已经转为中文摘要"],
        current_workarounds=[workaround],
        cluster_confidence=0.55,
        cluster_method="rule_similarity_v1",
    )


def test_similar_clusters_score_higher_than_unrelated_clusters() -> None:
    left = make_cluster(
        "cluster_000001",
        "投资人在产业跟踪中遇到的「信息分散、人工整理」问题",
        "投资人在人工智能产业跟踪中遇到信息分散和人工整理低效的问题。",
    )
    related = make_cluster(
        "cluster_000002",
        "研究员在产业跟踪中遇到的「信息分散、人工整理」问题",
        "研究员在人工智能产业跟踪中也需要处理信息分散和人工整理低效的问题。",
        persona="researcher",
    )
    unrelated = make_cluster(
        "cluster_000003",
        "开发者在工具链中遇到的「文档不完整」问题",
        "开发者在查找 SDK 示例时遇到文档不完整和检索困难。",
        persona="developer",
        domain="developer_workflow",
        pain="文档不完整，检索困难",
        workaround="搜索旧 issue",
    )

    related_score = cluster_merge_similarity(left, related).total
    unrelated_score = cluster_merge_similarity(left, unrelated).total

    assert related_score > unrelated_score
    assert related_score >= 60


def test_field_scores_and_shared_keywords_are_reported() -> None:
    left = make_cluster(
        "cluster_000001",
        "投资人在产业跟踪中遇到的「信息分散」问题",
        "投资人跟踪人工智能产业时反复遇到信息分散。",
    )
    right = make_cluster(
        "cluster_000002",
        "投资人在产业跟踪中遇到的「信息分散、人工整理」问题",
        "投资人跟踪人工智能产业时反复遇到信息分散和人工整理低效。",
    )

    result = cluster_merge_similarity(left, right)

    assert result.field_scores["title_similarity"] > 0
    assert result.field_scores["pain_description_similarity"] > 0
    assert "investor" in result.shared_personas
    assert "ai_investment_research" in result.shared_domain_tags
    assert "信息分散" in shared_keywords(left, right)
