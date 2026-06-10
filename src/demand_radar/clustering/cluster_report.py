"""Demand cluster report generation for Stage 2."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from demand_radar.clustering.cluster_store import (
    get_latest_cluster_review,
    load_cluster_reviews,
    load_demand_clusters,
)
from demand_radar.state.processed_store import load_pain_points
from demand_radar.state.raw_store import read_jsonl, utc_now_iso


PERSONA_LABELS = {
    "investor": "投资人",
    "researcher": "研究员",
    "founder": "创始人",
    "content_team": "内容团队",
    "developer": "开发者",
    "operator": "运营",
    "strategy_bd": "战略与商务拓展",
}

DOMAIN_LABELS = {
    "ai_investment_research": "人工智能投资研究",
    "ai_hardtech": "人工智能硬科技",
    "content_production": "内容生产",
    "enterprise_knowledge_workflow": "企业知识工作流",
    "ai_agent_workflow": "人工智能智能体工作流",
    "developer_workflow": "开发者工具链",
    "general_workflow": "相关工作流",
}


class ClusterReportSummary(BaseModel):
    pain_points: int
    demand_clusters: int
    singleton_clusters: int
    reviewed_clusters: int
    invalid_clusters: int
    cluster_reviews: int
    generated_at: str


def build_cluster_report(
    pain_points_path: str | Path = "data/processed/pain_points.jsonl",
    clusters_path: str | Path = "data/processed/demand_clusters.jsonl",
    cluster_reviews_path: str | Path = "data/processed/cluster_reviews.jsonl",
    invalid_clusters_path: str | Path = "data/quarantine/invalid_clusters.jsonl",
    report_path: str | Path = "outputs/demand_clusters_report.md",
    summary_path: str | Path = "outputs/run_summary.json",
) -> ClusterReportSummary:
    pain_points = load_pain_points(pain_points_path)
    clusters = load_demand_clusters(clusters_path)
    reviews = load_cluster_reviews(cluster_reviews_path)
    invalid_clusters = read_jsonl(invalid_clusters_path)
    reviewed_cluster_ids = {review.cluster_id for review in reviews}
    summary = ClusterReportSummary(
        pain_points=len(pain_points),
        demand_clusters=len(clusters),
        singleton_clusters=sum(1 for cluster in clusters if cluster.evidence_count == 1),
        reviewed_clusters=len(reviewed_cluster_ids),
        invalid_clusters=len(invalid_clusters),
        cluster_reviews=len(reviews),
        generated_at=utc_now_iso(),
    )
    _write_markdown(clusters, reviews, summary, report_path)
    _merge_run_summary(summary, summary_path)
    return summary


def _write_markdown(
    clusters: list,
    reviews: list,
    summary: ClusterReportSummary,
    report_path: str | Path,
) -> None:
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Demand Clusters Report",
        "",
        "## Run Summary",
        "",
        f"- Pain points: {summary.pain_points}",
        f"- Demand clusters: {summary.demand_clusters}",
        f"- Singleton clusters: {summary.singleton_clusters}",
        f"- Reviewed clusters: {summary.reviewed_clusters}",
        f"- Invalid clusters: {summary.invalid_clusters}",
        f"- Generated at: {summary.generated_at}",
        "",
        "## Demand Clusters",
        "",
    ]
    if not clusters:
        lines.append("No demand clusters generated.")
    for index, cluster in enumerate(clusters, start=1):
        latest_review = get_latest_cluster_review(cluster.cluster_id, reviews=reviews)
        lines.extend(_cluster_lines(index, cluster, latest_review))
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _cluster_lines(index: int, cluster, latest_review) -> list[str]:
    review_status = _review_label(latest_review.label) if latest_review else "未审核"
    personas = _label_values(cluster.personas, PERSONA_LABELS, "未标注")
    domain_tags = _label_values(cluster.domain_tags, DOMAIN_LABELS, "未标注")
    return [
        f"### {index}. {cluster.cluster_title_zh}",
        "",
        f"需求摘要：{cluster.cluster_summary_zh}",
        f"目标用户：{personas}",
        f"相关领域：{domain_tags}",
        f"证据数量：{cluster.evidence_count}",
        f"来源数量：{cluster.source_count}",
        f"代表性痛点：{'；'.join(cluster.representative_pain_descriptions)}",
        f"代表性证据：{'；'.join(cluster.representative_quotes)}",
        f"当前替代方案：{'；'.join(cluster.current_workarounds)}",
        f"聚类置信度：{cluster.cluster_confidence:.2f}",
        f"审核状态：{review_status}",
        "",
        "---",
        "",
    ]


def _label_values(values: list[str], labels: dict[str, str], fallback: str) -> str:
    cleaned = [labels.get(value, value) for value in values if value]
    return "、".join(cleaned) if cleaned else fallback


def _review_label(label: str) -> str:
    labels = {
        "good_cluster": "通过",
        "too_broad": "过宽",
        "too_narrow": "过窄",
        "wrong_grouping": "分组错误",
        "duplicate_cluster": "重复主题",
        "bad_title": "标题问题",
        "should_merge": "应合并",
        "should_split": "应拆分",
        "not_a_real_demand": "不是真需求",
    }
    return labels.get(label, label)


def _merge_run_summary(summary: ClusterReportSummary, summary_path: str | Path) -> None:
    summary_path = Path(summary_path)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if summary_path.exists() and summary_path.read_text(encoding="utf-8").strip():
        existing = json.loads(summary_path.read_text(encoding="utf-8"))
    existing.update(summary.model_dump(mode="json"))
    summary_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
