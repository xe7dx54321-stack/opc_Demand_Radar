"""Reports for Stage 2.7 semantic merge judgments."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from pydantic import BaseModel

from demand_radar.clustering.merge_store import load_merge_candidates
from demand_radar.semantic_merge.semantic_merge_store import (
    load_ai_reviewed_cluster_groups,
    load_human_exception_items,
    load_semantic_merge_judgments,
)
from demand_radar.state.raw_store import utc_now_iso


class SemanticMergeReportSummary(BaseModel):
    merge_candidates: int
    judgments: int
    auto_confirmed: int
    auto_rejected: int
    human_exceptions: int
    decision_counts: dict[str, int]
    human_exception_rate: float | None
    generated_at: str


class HumanExceptionReportSummary(BaseModel):
    exceptions: int
    high_priority: int
    medium_priority: int
    low_priority: int
    generated_at: str


class AIReviewedGroupsReportSummary(BaseModel):
    ai_reviewed_groups: int
    included_clusters: int
    included_pain_points: int
    generated_at: str


def build_semantic_merge_report(
    candidates_path: str | Path = "data/processed/cluster_merge_candidates.jsonl",
    judgments_path: str | Path = "data/processed/semantic_merge_judgments.jsonl",
    exceptions_path: str | Path = "data/processed/human_exception_queue.jsonl",
    report_path: str | Path = "outputs/semantic_merge_judgment_report.md",
    summary_path: str | Path = "outputs/run_summary.json",
) -> SemanticMergeReportSummary:
    candidates = load_merge_candidates(candidates_path)
    judgments = load_semantic_merge_judgments(judgments_path)
    exceptions = load_human_exception_items(exceptions_path)
    decision_counts = Counter(judgment.decision for judgment in judgments)
    summary = SemanticMergeReportSummary(
        merge_candidates=len(candidates),
        judgments=len(judgments),
        auto_confirmed=sum(1 for judgment in judgments if judgment.auto_action == "auto_confirm"),
        auto_rejected=sum(1 for judgment in judgments if judgment.auto_action == "auto_reject"),
        human_exceptions=len(exceptions),
        decision_counts={key: decision_counts[key] for key in ("confirm_merge", "reject_merge", "maybe_merge")},
        human_exception_rate=round(len(exceptions) / len(judgments), 4) if judgments else None,
        generated_at=utc_now_iso(),
    )
    _write_semantic_merge_report(judgments, exceptions, summary, report_path)
    _merge_run_summary(
        {
            "semantic_judgments": summary.judgments,
            "auto_confirmed": summary.auto_confirmed,
            "auto_rejected": summary.auto_rejected,
            "human_exceptions": summary.human_exceptions,
            "human_exception_rate": summary.human_exception_rate,
            "semantic_merge_report_generated_at": summary.generated_at,
        },
        summary_path,
    )
    return summary


def build_human_exception_report(
    exceptions_path: str | Path = "data/processed/human_exception_queue.jsonl",
    report_path: str | Path = "outputs/human_exception_queue_report.md",
    summary_path: str | Path = "outputs/run_summary.json",
) -> HumanExceptionReportSummary:
    exceptions = load_human_exception_items(exceptions_path)
    priority_counts = Counter(item.priority for item in exceptions)
    summary = HumanExceptionReportSummary(
        exceptions=len(exceptions),
        high_priority=priority_counts["high"],
        medium_priority=priority_counts["medium"],
        low_priority=priority_counts["low"],
        generated_at=utc_now_iso(),
    )
    _write_human_exception_report(exceptions, summary, report_path)
    _merge_run_summary(
        {
            "human_exceptions": summary.exceptions,
            "high_priority_exceptions": summary.high_priority,
            "medium_priority_exceptions": summary.medium_priority,
            "low_priority_exceptions": summary.low_priority,
            "human_exception_report_generated_at": summary.generated_at,
        },
        summary_path,
    )
    return summary


def build_ai_reviewed_groups_report(
    groups_path: str | Path = "data/processed/ai_reviewed_cluster_groups.jsonl",
    report_path: str | Path = "outputs/ai_reviewed_cluster_groups_report.md",
    summary_path: str | Path = "outputs/run_summary.json",
) -> AIReviewedGroupsReportSummary:
    groups = load_ai_reviewed_cluster_groups(groups_path)
    summary = AIReviewedGroupsReportSummary(
        ai_reviewed_groups=len(groups),
        included_clusters=len({cluster_id for group in groups for cluster_id in group.cluster_ids}),
        included_pain_points=len({pain_id for group in groups for pain_id in group.related_pain_point_ids}),
        generated_at=utc_now_iso(),
    )
    _write_ai_reviewed_groups_report(groups, summary, report_path)
    _merge_run_summary(
        {
            "ai_reviewed_groups": summary.ai_reviewed_groups,
            "ai_reviewed_included_clusters": summary.included_clusters,
            "ai_reviewed_included_pain_points": summary.included_pain_points,
            "ai_reviewed_groups_report_generated_at": summary.generated_at,
        },
        summary_path,
    )
    return summary


def _write_semantic_merge_report(
    judgments: list,
    exceptions: list,
    summary: SemanticMergeReportSummary,
    report_path: str | Path,
) -> None:
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    exception_ids = {item.judgment_id for item in exceptions}
    lines = [
        "# Semantic Merge Judgment Report",
        "",
        "## Run Summary",
        "",
        f"- Merge candidates: {summary.merge_candidates}",
        f"- Judgments: {summary.judgments}",
        f"- Auto confirmed: {summary.auto_confirmed}",
        f"- Auto rejected: {summary.auto_rejected}",
        f"- Human exceptions: {summary.human_exceptions}",
        f"- Generated at: {summary.generated_at}",
        "",
        "## Decision Breakdown",
        "",
        "| Decision | Count |",
        "|---|---:|",
        f"| confirm_merge | {summary.decision_counts.get('confirm_merge', 0)} |",
        f"| reject_merge | {summary.decision_counts.get('reject_merge', 0)} |",
        f"| maybe_merge | {summary.decision_counts.get('maybe_merge', 0)} |",
        "",
        "## Auto Confirmed Merges",
        "",
    ]
    auto_confirmed = [judgment for judgment in judgments if judgment.auto_action == "auto_confirm"]
    if not auto_confirmed:
        lines.append("No auto confirmed merges.")
    for index, judgment in enumerate(auto_confirmed, start=1):
        lines.extend(_auto_confirm_lines(index, judgment))

    lines.extend(["", "## Auto Rejected Merges", ""])
    auto_rejected = [judgment for judgment in judgments if judgment.auto_action == "auto_reject"]
    if not auto_rejected:
        lines.append("No auto rejected merges.")
    for index, judgment in enumerate(auto_rejected, start=1):
        lines.extend(_auto_reject_lines(index, judgment))

    lines.extend(["", "## Human Exceptions", ""])
    human_exception_judgments = [judgment for judgment in judgments if judgment.judgment_id in exception_ids]
    if not human_exception_judgments:
        lines.append("No human exceptions.")
    for index, judgment in enumerate(human_exception_judgments, start=1):
        lines.extend(_human_exception_lines(index, judgment))
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _write_human_exception_report(
    exceptions: list,
    summary: HumanExceptionReportSummary,
    report_path: str | Path,
) -> None:
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Human Exception Queue Report",
        "",
        "## Summary",
        "",
        f"- Exceptions: {summary.exceptions}",
        f"- High priority: {summary.high_priority}",
        f"- Medium priority: {summary.medium_priority}",
        f"- Low priority: {summary.low_priority}",
        f"- Generated at: {summary.generated_at}",
        "",
        "## Exceptions",
        "",
    ]
    if not exceptions:
        lines.append("No human exceptions.")
    for index, item in enumerate(exceptions, start=1):
        lines.extend(
            [
                f"### {index}. Exception",
                "",
                f"Candidate: {item.merge_candidate_id}",
                f"Clusters: {item.cluster_id_a} / {item.cluster_id_b}",
                f"Decision: {item.decision}",
                f"Confidence: {item.confidence:.2f}",
                f"Priority: {item.priority}",
                f"Reason: {item.exception_reason}",
                f"Conflict Flags: {_join(item.conflict_flags)}",
                f"AI Reason: {item.reason_zh}",
                f"Recommended Human Action: {_recommended_action(item)}",
                "",
                "---",
                "",
            ]
        )
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _write_ai_reviewed_groups_report(
    groups: list,
    summary: AIReviewedGroupsReportSummary,
    report_path: str | Path,
) -> None:
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# AI Reviewed Cluster Groups Report",
        "",
        "## Summary",
        "",
        f"- AI reviewed groups: {summary.ai_reviewed_groups}",
        f"- Included clusters: {summary.included_clusters}",
        f"- Included pain points: {summary.included_pain_points}",
        f"- Generated at: {summary.generated_at}",
        "",
        "## Groups",
        "",
    ]
    if not groups:
        lines.append("No AI reviewed cluster groups generated.")
    for index, group in enumerate(groups, start=1):
        lines.extend(
            [
                f"### {index}. {group.group_title_zh}",
                "",
                f"Group ID: {group.group_id}",
                f"Clusters: {_join(group.cluster_ids)}",
                f"Evidence count: {group.evidence_count}",
                f"Personas: {_join(group.personas)}",
                f"Domain tags: {_join(group.domain_tags)}",
                f"Created from judgments: {_join(group.created_from_judgment_ids)}",
                "",
                "需求摘要：",
                group.group_summary_zh,
                "",
                f"代表性痛点：{_join(group.representative_pain_descriptions)}",
                f"代表性证据：{_join(group.representative_quotes)}",
                f"当前替代方案：{_join(group.current_workarounds)}",
                "",
                "---",
                "",
            ]
        )
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _auto_confirm_lines(index: int, judgment) -> list[str]:
    return [
        f"### {index}. 中文合并建议",
        "",
        f"Candidate: {judgment.merge_candidate_id}",
        f"Clusters: {judgment.cluster_id_a} / {judgment.cluster_id_b}",
        f"Confidence: {judgment.confidence:.2f}",
        f"Reason: {judgment.reason_zh}",
        f"Suggested Group Title: {judgment.suggested_group_title_zh or 'n/a'}",
        f"Suggested Group Summary: {judgment.suggested_group_summary_zh or 'n/a'}",
        f"Evidence Alignment: {judgment.evidence_alignment_zh or 'n/a'}",
        f"Workflow Judgment: {judgment.workflow_judgment_zh or 'n/a'}",
        "",
        "---",
        "",
    ]


def _auto_reject_lines(index: int, judgment) -> list[str]:
    return [
        f"### {index}. 拒绝合并",
        "",
        f"Candidate: {judgment.merge_candidate_id}",
        f"Clusters: {judgment.cluster_id_a} / {judgment.cluster_id_b}",
        f"Confidence: {judgment.confidence:.2f}",
        f"Reason: {judgment.reason_zh}",
        f"Conflict Flags: {_join(judgment.conflict_flags)}",
        "",
        "---",
        "",
    ]


def _human_exception_lines(index: int, judgment) -> list[str]:
    return [
        f"### {index}. 需要人工查看",
        "",
        f"Candidate: {judgment.merge_candidate_id}",
        f"Decision: {judgment.decision}",
        f"Confidence: {judgment.confidence:.2f}",
        f"Exception Reason: {judgment.auto_action}",
        f"Conflict Flags: {_join(judgment.conflict_flags)}",
        f"Reason: {judgment.reason_zh}",
        "",
        "---",
        "",
    ]


def _recommended_action(item) -> str:
    if item.priority == "high":
        return "优先人工判断是否应合并，并把错误原因沉淀为校准样本。"
    if item.decision == "maybe_merge":
        return "人工确认是否属于同一工作流需求。"
    return "抽检 AI 判断边界，必要时修正为确认或拒绝。"


def _join(values: list[str]) -> str:
    cleaned = [str(value).strip() for value in values if str(value).strip()]
    return "、".join(cleaned) if cleaned else "n/a"


def _merge_run_summary(payload: dict, summary_path: str | Path) -> None:
    summary_path = Path(summary_path)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if summary_path.exists() and summary_path.read_text(encoding="utf-8").strip():
        existing = json.loads(summary_path.read_text(encoding="utf-8"))
    existing.update(payload)
    summary_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
