"""Reports for Stage 2.5 merge suggestions and reviewed cluster groups."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from pydantic import BaseModel

from demand_radar.clustering.cluster_store import load_demand_clusters
from demand_radar.clustering.merge_schema import ClusterGroupReview
from demand_radar.clustering.merge_store import (
    get_latest_review_for_candidate,
    load_cluster_group_reviews,
    load_merge_candidates,
    load_reviewed_cluster_groups,
)
from demand_radar.state.raw_store import utc_now_iso


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

REVIEW_LABELS = {
    "confirm_merge": "确认合并",
    "reject_merge": "不合并",
    "maybe_merge": "暂时不确定",
    "wrong_reason": "理由不对",
    "bad_title": "标题不好",
    "needs_split": "需要拆分",
    "duplicate_candidate": "重复建议",
    "not_same_demand": "不是同一需求",
}


class MergeReportSummary(BaseModel):
    demand_clusters: int
    merge_candidates: int
    strong_candidates: int
    medium_candidates: int
    reviewed_candidates: int
    confirmed_merges: int
    rejected_merges: int
    generated_at: str


class ReviewedGroupsReportSummary(BaseModel):
    reviewed_groups: int
    included_clusters: int
    included_pain_points: int
    generated_at: str


def build_merge_report(
    clusters_path: str | Path = "data/processed/demand_clusters.jsonl",
    candidates_path: str | Path = "data/processed/cluster_merge_candidates.jsonl",
    reviews_path: str | Path = "data/processed/cluster_group_reviews.jsonl",
    report_path: str | Path = "outputs/cluster_merge_suggestions.md",
    summary_path: str | Path = "outputs/run_summary.json",
) -> MergeReportSummary:
    clusters = load_demand_clusters(clusters_path)
    candidates = load_merge_candidates(candidates_path)
    reviews = load_cluster_group_reviews(reviews_path)
    latest_reviews = [
        review
        for candidate in candidates
        if (
            review := get_latest_review_for_candidate(
                candidate.merge_candidate_id,
                reviews,
                cluster_id_a=candidate.cluster_id_a,
                cluster_id_b=candidate.cluster_id_b,
            )
        )
        is not None
    ]
    label_counts = Counter(review.label for review in latest_reviews)
    summary = MergeReportSummary(
        demand_clusters=len(clusters),
        merge_candidates=len(candidates),
        strong_candidates=sum(1 for candidate in candidates if candidate.strength == "strong"),
        medium_candidates=sum(1 for candidate in candidates if candidate.strength == "medium"),
        reviewed_candidates=len(latest_reviews),
        confirmed_merges=label_counts["confirm_merge"],
        rejected_merges=label_counts["reject_merge"] + label_counts["not_same_demand"],
        generated_at=utc_now_iso(),
    )
    _write_merge_report(candidates, reviews, summary, report_path)
    _merge_run_summary(summary.model_dump(mode="json"), summary_path)
    return summary


def build_reviewed_groups_report(
    groups_path: str | Path = "data/processed/reviewed_cluster_groups.jsonl",
    report_path: str | Path = "outputs/reviewed_cluster_groups_report.md",
    summary_path: str | Path = "outputs/run_summary.json",
) -> ReviewedGroupsReportSummary:
    groups = load_reviewed_cluster_groups(groups_path)
    summary = ReviewedGroupsReportSummary(
        reviewed_groups=len(groups),
        included_clusters=len({cluster_id for group in groups for cluster_id in group.cluster_ids}),
        included_pain_points=len({pain_id for group in groups for pain_id in group.related_pain_point_ids}),
        generated_at=utc_now_iso(),
    )
    _write_reviewed_groups_report(groups, summary, report_path)
    _merge_run_summary(summary.model_dump(mode="json"), summary_path)
    return summary


def _write_merge_report(
    candidates: list,
    reviews: list[ClusterGroupReview],
    summary: MergeReportSummary,
    report_path: str | Path,
) -> None:
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Cluster Merge Suggestions Report",
        "",
        "## Run Summary",
        "",
        f"- Demand clusters: {summary.demand_clusters}",
        f"- Merge candidates: {summary.merge_candidates}",
        f"- Strong candidates: {summary.strong_candidates}",
        f"- Medium candidates: {summary.medium_candidates}",
        f"- Reviewed candidates: {summary.reviewed_candidates}",
        f"- Confirmed merges: {summary.confirmed_merges}",
        f"- Rejected merges: {summary.rejected_merges}",
        f"- Generated at: {summary.generated_at}",
        "",
        "## Merge Candidates",
        "",
    ]
    if not candidates:
        lines.append("No merge candidates generated.")
    for index, candidate in enumerate(candidates, start=1):
        latest_review = get_latest_review_for_candidate(
            candidate.merge_candidate_id,
            reviews,
            cluster_id_a=candidate.cluster_id_a,
            cluster_id_b=candidate.cluster_id_b,
        )
        lines.extend(_merge_candidate_lines(index, candidate, latest_review))
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _merge_candidate_lines(index: int, candidate, latest_review: ClusterGroupReview | None) -> list[str]:
    latest = _review_label(latest_review.label) if latest_review else "未审核"
    return [
        f"### {index}. 合并建议",
        "",
        f"Candidate ID: {candidate.merge_candidate_id}",
        f"Cluster A: {candidate.cluster_id_a} / {candidate.title_a}",
        f"Cluster B: {candidate.cluster_id_b} / {candidate.title_b}",
        f"Similarity Score: {candidate.similarity_score:.2f}",
        f"Strength: {_strength_label(candidate.strength)}",
        "",
        "建议理由：",
        candidate.merge_reason_zh,
        "",
        "风险提示：",
        candidate.risk_note_zh or "暂无明显风险提示。",
        "",
        "相似诊断：",
        f"- Title similarity: {candidate.field_scores.get('title_similarity', 0):.2f}",
        f"- Summary similarity: {candidate.field_scores.get('summary_similarity', 0):.2f}",
        f"- Pain description similarity: {candidate.field_scores.get('pain_description_similarity', 0):.2f}",
        f"- Workaround similarity: {candidate.field_scores.get('workaround_similarity', 0):.2f}",
        f"- Persona similarity: {candidate.field_scores.get('persona_similarity', 0):.2f}",
        f"- Domain similarity: {candidate.field_scores.get('domain_similarity', 0):.2f}",
        "",
        f"共享关键词：{'、'.join(candidate.shared_keywords) or '暂无'}",
        "",
        "Cluster A 代表证据：",
        _list_line(candidate.representative_quotes_a),
        "",
        "Cluster B 代表证据：",
        _list_line(candidate.representative_quotes_b),
        "",
        f"Latest Review: {latest}",
        "",
        "---",
        "",
    ]


def _write_reviewed_groups_report(groups: list, summary: ReviewedGroupsReportSummary, report_path: str | Path) -> None:
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Reviewed Cluster Groups Report",
        "",
        "## Run Summary",
        "",
        f"- Reviewed groups: {summary.reviewed_groups}",
        f"- Included clusters: {summary.included_clusters}",
        f"- Included pain points: {summary.included_pain_points}",
        f"- Generated at: {summary.generated_at}",
        "",
        "## Reviewed Groups",
        "",
    ]
    if not groups:
        lines.append("No reviewed cluster groups generated.")
    for index, group in enumerate(groups, start=1):
        lines.extend(_reviewed_group_lines(index, group))
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _reviewed_group_lines(index: int, group) -> list[str]:
    return [
        f"### {index}. {group.group_title_zh}",
        "",
        f"Group ID: {group.group_id}",
        f"Clusters: {'、'.join(group.cluster_ids)}",
        f"Personas: {_label_values(group.personas, PERSONA_LABELS, '未标注')}",
        f"Domain tags: {_label_values(group.domain_tags, DOMAIN_LABELS, '未标注')}",
        f"Evidence count: {group.evidence_count}",
        f"Source count: {group.source_count}",
        "",
        "需求摘要：",
        group.group_summary_zh,
        "",
        f"代表性痛点：{'；'.join(group.representative_pain_descriptions) or '暂无'}",
        f"代表性证据：{'；'.join(group.representative_quotes) or '暂无'}",
        f"当前替代方案：{'；'.join(group.current_workarounds) or '暂无'}",
        "",
        "---",
        "",
    ]


def _list_line(values: list[str]) -> str:
    if not values:
        return "- 暂无"
    return "\n".join(f"- {value}" for value in values)


def _review_label(label: str) -> str:
    return REVIEW_LABELS.get(label, label)


def _strength_label(strength: str) -> str:
    return {"strong": "强", "medium": "中", "weak": "弱"}.get(strength, strength)


def _label_values(values: list[str], labels: dict[str, str], fallback: str) -> str:
    cleaned = [labels.get(value, value) for value in values if value]
    return "、".join(cleaned) if cleaned else fallback


def _merge_run_summary(payload: dict, summary_path: str | Path) -> None:
    summary_path = Path(summary_path)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if summary_path.exists() and summary_path.read_text(encoding="utf-8").strip():
        existing = json.loads(summary_path.read_text(encoding="utf-8"))
    existing.update(payload)
    summary_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
