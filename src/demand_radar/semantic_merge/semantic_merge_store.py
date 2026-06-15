"""Persistence and AI reviewed group building for semantic merge judgments."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from pydantic import ValidationError

from demand_radar.clustering.cluster_schema import DemandCluster
from demand_radar.clustering.cluster_store import load_demand_clusters
from demand_radar.semantic_merge.exception_queue import (
    build_exception_item,
    should_enter_exception_queue,
)
from demand_radar.semantic_merge.semantic_merge_schema import (
    AIReviewedClusterGroup,
    HumanExceptionItem,
    SemanticMergeHumanAudit,
    SemanticMergeJudgment,
)
from demand_radar.state.raw_store import next_id, next_ids, read_jsonl, write_jsonl


DEFAULT_SEMANTIC_MERGE_JUDGMENTS_PATH = Path("data/processed/semantic_merge_judgments.jsonl")
DEFAULT_HUMAN_EXCEPTION_QUEUE_PATH = Path("data/processed/human_exception_queue.jsonl")
DEFAULT_AI_REVIEWED_GROUPS_PATH = Path("data/processed/ai_reviewed_cluster_groups.jsonl")
DEFAULT_SEMANTIC_HUMAN_AUDITS_PATH = Path("data/processed/semantic_merge_human_audits.jsonl")


def load_semantic_merge_judgments(
    path: str | Path = DEFAULT_SEMANTIC_MERGE_JUDGMENTS_PATH,
) -> list[SemanticMergeJudgment]:
    return [SemanticMergeJudgment.model_validate(row) for row in read_jsonl(path)]


def write_semantic_merge_judgments(
    judgments: Iterable[SemanticMergeJudgment],
    path: str | Path = DEFAULT_SEMANTIC_MERGE_JUDGMENTS_PATH,
) -> int:
    return write_jsonl(path, judgments)


def load_human_exception_items(
    path: str | Path = DEFAULT_HUMAN_EXCEPTION_QUEUE_PATH,
) -> list[HumanExceptionItem]:
    return [HumanExceptionItem.model_validate(row) for row in read_jsonl(path)]


def write_human_exception_items(
    items: Iterable[HumanExceptionItem],
    path: str | Path = DEFAULT_HUMAN_EXCEPTION_QUEUE_PATH,
) -> int:
    return write_jsonl(path, items)


def build_human_exception_queue(judgments: list[SemanticMergeJudgment]) -> list[HumanExceptionItem]:
    exception_source = [judgment for judgment in judgments if should_enter_exception_queue(judgment)]
    exception_ids = next_ids("human_exception", [], len(exception_source))
    return [
        build_exception_item(judgment, exception_id)
        for exception_id, judgment in zip(exception_ids, exception_source, strict=True)
    ]


def load_ai_reviewed_cluster_groups(
    path: str | Path = DEFAULT_AI_REVIEWED_GROUPS_PATH,
) -> list[AIReviewedClusterGroup]:
    return [AIReviewedClusterGroup.model_validate(row) for row in read_jsonl(path)]


def write_ai_reviewed_cluster_groups(
    groups: Iterable[AIReviewedClusterGroup],
    path: str | Path = DEFAULT_AI_REVIEWED_GROUPS_PATH,
) -> int:
    return write_jsonl(path, groups)


def build_ai_reviewed_cluster_groups(
    clusters_path: str | Path = "data/processed/demand_clusters.jsonl",
    judgments_path: str | Path = DEFAULT_SEMANTIC_MERGE_JUDGMENTS_PATH,
    groups_path: str | Path = DEFAULT_AI_REVIEWED_GROUPS_PATH,
    invalid_groups_path: str | Path = "data/quarantine/invalid_ai_reviewed_groups.jsonl",
) -> list[AIReviewedClusterGroup]:
    clusters = load_demand_clusters(clusters_path)
    judgments = load_semantic_merge_judgments(judgments_path)
    groups = _build_groups_from_auto_confirmed_judgments(clusters, judgments)
    valid_groups: list[AIReviewedClusterGroup] = []
    invalid_rows: list[dict[str, object]] = []

    for group in groups:
        try:
            validated = AIReviewedClusterGroup.model_validate(group.model_dump(mode="json"))
        except (ValidationError, ValueError) as exc:
            invalid_rows.append({"reason": "ai_reviewed_group_invalid", "errors": str(exc), "group": group.model_dump(mode="json")})
            continue
        if not ai_reviewed_cluster_group_gate(validated):
            invalid_rows.append(
                {"reason": "ai_reviewed_group_gate_failed", "group": validated.model_dump(mode="json")}
            )
            continue
        valid_groups.append(validated)

    write_ai_reviewed_cluster_groups(valid_groups, groups_path)
    write_jsonl(invalid_groups_path, invalid_rows)
    return valid_groups


def ai_reviewed_cluster_group_gate(group: AIReviewedClusterGroup) -> bool:
    return (
        len(group.cluster_ids) >= 2
        and bool(group.related_pain_point_ids)
        and bool(group.group_title_zh.strip())
        and bool(group.group_summary_zh.strip())
        and group.evidence_count >= 2
        and bool(group.created_from_judgment_ids)
    )


def append_semantic_merge_human_audit(
    judgment_id: str,
    merge_candidate_id: str,
    label: str,
    reviewer_note: str | None = None,
    corrected_decision: str | None = None,
    path: str | Path = DEFAULT_SEMANTIC_HUMAN_AUDITS_PATH,
) -> SemanticMergeHumanAudit:
    existing = load_semantic_merge_human_audits(path)
    audit = SemanticMergeHumanAudit(
        audit_id=next_id("semantic_merge_audit", [item.audit_id for item in existing]),
        judgment_id=judgment_id,
        merge_candidate_id=merge_candidate_id,
        label=label,
        reviewer_note=reviewer_note,
        corrected_decision=corrected_decision,
    )
    write_jsonl(path, [audit], append=True)
    return audit


def load_semantic_merge_human_audits(
    path: str | Path = DEFAULT_SEMANTIC_HUMAN_AUDITS_PATH,
) -> list[SemanticMergeHumanAudit]:
    return [SemanticMergeHumanAudit.model_validate(row) for row in read_jsonl(path)]


def get_latest_audit_for_judgment(
    judgment_id: str,
    audits: list[SemanticMergeHumanAudit] | None = None,
    path: str | Path = DEFAULT_SEMANTIC_HUMAN_AUDITS_PATH,
) -> SemanticMergeHumanAudit | None:
    audit_list = audits if audits is not None else load_semantic_merge_human_audits(path)
    matching = [audit for audit in audit_list if audit.judgment_id == judgment_id]
    return matching[-1] if matching else None


def _build_groups_from_auto_confirmed_judgments(
    clusters: list[DemandCluster],
    judgments: list[SemanticMergeJudgment],
) -> list[AIReviewedClusterGroup]:
    confirmed = [judgment for judgment in judgments if judgment.auto_action == "auto_confirm"]
    if not confirmed:
        return []

    cluster_by_id = {cluster.cluster_id: cluster for cluster in clusters}
    parent: dict[str, str] = {}

    def find(cluster_id: str) -> str:
        parent.setdefault(cluster_id, cluster_id)
        while parent[cluster_id] != cluster_id:
            parent[cluster_id] = parent[parent[cluster_id]]
            cluster_id = parent[cluster_id]
        return cluster_id

    def union(left: str, right: str) -> None:
        root_left = find(left)
        root_right = find(right)
        if root_left != root_right:
            parent[root_right] = root_left

    for judgment in confirmed:
        if judgment.cluster_id_a in cluster_by_id and judgment.cluster_id_b in cluster_by_id:
            union(judgment.cluster_id_a, judgment.cluster_id_b)

    component_ids: dict[str, list[str]] = {}
    for cluster_id in parent:
        component_ids.setdefault(find(cluster_id), []).append(cluster_id)

    group_ids = next_ids("ai_cluster_group", [], len(component_ids))
    groups: list[AIReviewedClusterGroup] = []
    for group_id, cluster_ids in zip(group_ids, component_ids.values(), strict=True):
        component_clusters = [cluster_by_id[cluster_id] for cluster_id in sorted(cluster_ids)]
        component_judgments = [
            judgment
            for judgment in confirmed
            if judgment.cluster_id_a in cluster_ids and judgment.cluster_id_b in cluster_ids
        ]
        groups.append(_build_ai_group(group_id, component_clusters, component_judgments))
    return groups


def _build_ai_group(
    group_id: str,
    clusters: list[DemandCluster],
    judgments: list[SemanticMergeJudgment],
) -> AIReviewedClusterGroup:
    latest_title = _latest_expected(judgments, "suggested_group_title_zh")
    latest_summary = _latest_expected(judgments, "suggested_group_summary_zh")
    title_source = max(clusters, key=lambda cluster: (cluster.evidence_count, cluster.cluster_title_zh))
    return AIReviewedClusterGroup(
        group_id=group_id,
        group_title_zh=latest_title or title_source.cluster_title_zh,
        group_summary_zh=latest_summary or _truncate(" ".join(_unique(cluster.cluster_summary_zh for cluster in clusters)), 300),
        cluster_ids=_unique(cluster.cluster_id for cluster in clusters),
        related_pain_point_ids=_unique(
            pain_id for cluster in clusters for pain_id in cluster.related_pain_point_ids
        ),
        personas=_unique(persona for cluster in clusters for persona in cluster.personas),
        domain_tags=_unique(tag for cluster in clusters for tag in cluster.domain_tags),
        batch_ids=_unique(batch_id for cluster in clusters for batch_id in cluster.batch_ids),
        evidence_count=sum(cluster.evidence_count for cluster in clusters),
        source_count=sum(cluster.source_count for cluster in clusters),
        representative_pain_descriptions=_unique(
            item for cluster in clusters for item in cluster.representative_pain_descriptions
        )[:5],
        representative_quotes=_unique(item for cluster in clusters for item in cluster.representative_quotes)[:5],
        current_workarounds=_unique(item for cluster in clusters for item in cluster.current_workarounds)[:5],
        created_from_judgment_ids=_unique(judgment.judgment_id for judgment in judgments),
    )


def _latest_expected(judgments: list[SemanticMergeJudgment], field_name: str) -> str:
    for judgment in reversed(judgments):
        value = getattr(judgment, field_name)
        if value:
            return value
    return ""


def _unique(values: Iterable[str | None]) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in result:
            result.append(text)
    return result


def _truncate(text: str, max_chars: int) -> str:
    text = text.strip()
    return text if len(text) <= max_chars else text[: max_chars - 1] + "…"
