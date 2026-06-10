"""Generate Stage 2.5 cluster merge candidates from demand clusters."""

from __future__ import annotations

from itertools import combinations
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from demand_radar.clustering.cluster_schema import DemandCluster
from demand_radar.clustering.cluster_store import load_demand_clusters
from demand_radar.clustering.merge_schema import ClusterMergeCandidate
from demand_radar.clustering.merge_similarity import DEFAULT_MERGE_WEIGHTS, cluster_merge_similarity
from demand_radar.config.load_config import load_yaml
from demand_radar.state.raw_store import next_ids, write_jsonl


DEFAULT_MERGE_SUGGESTION_CONFIG = {
    "enabled": True,
    "candidate_threshold": 62,
    "strong_candidate_threshold": 75,
    "max_candidates_per_cluster": 5,
    "fields": DEFAULT_MERGE_WEIGHTS,
    "output": {"language": "zh", "max_reason_chars": 300},
}

PERSONA_ZH = {
    "investor": "投资人",
    "researcher": "研究员",
    "founder": "创始人",
    "content_team": "内容团队",
    "developer": "开发者",
    "operator": "运营",
    "strategy_bd": "战略与商务拓展",
}

DOMAIN_ZH = {
    "ai_investment_research": "人工智能投资研究",
    "ai_hardtech": "人工智能硬科技",
    "content_production": "内容生产",
    "enterprise_knowledge_workflow": "企业知识工作流",
    "ai_agent_workflow": "人工智能智能体工作流",
    "developer_workflow": "开发者工具链",
    "general_workflow": "相关工作流",
}


def suggest_cluster_merges(
    clusters_path: str | Path = "data/processed/demand_clusters.jsonl",
    candidates_path: str | Path = "data/processed/cluster_merge_candidates.jsonl",
    invalid_candidates_path: str | Path = "data/quarantine/invalid_merge_candidates.jsonl",
    config_path: str | Path = "configs/merge_suggestion_config.yaml",
) -> list[ClusterMergeCandidate]:
    config = _load_merge_config(config_path)
    clusters = load_demand_clusters(clusters_path)
    scored_pairs = _candidate_pairs(clusters, config)
    candidate_ids = next_ids("merge_candidate", [], len(scored_pairs))
    candidates: list[ClusterMergeCandidate] = []
    invalid_rows: list[dict[str, Any]] = []

    for candidate_id, (left, right, similarity) in zip(candidate_ids, scored_pairs, strict=True):
        payload = _candidate_payload(candidate_id, left, right, similarity, config)
        try:
            candidate = ClusterMergeCandidate.model_validate(payload)
        except (ValidationError, ValueError) as exc:
            invalid_rows.append(
                {
                    "merge_candidate_id": candidate_id,
                    "reason": "merge_candidate_invalid",
                    "errors": str(exc),
                    "payload": payload,
                }
            )
            continue
        if not merge_candidate_gate(candidate, float(config["candidate_threshold"])):
            invalid_rows.append(
                {
                    "merge_candidate_id": candidate.merge_candidate_id,
                    "reason": "merge_candidate_gate_failed",
                    "candidate": candidate.model_dump(mode="json"),
                }
            )
            continue
        candidates.append(candidate)

    write_jsonl(candidates_path, candidates)
    write_jsonl(invalid_candidates_path, invalid_rows)
    return candidates


def merge_candidate_gate(candidate: ClusterMergeCandidate, candidate_threshold: float) -> bool:
    return (
        bool(candidate.cluster_id_a)
        and bool(candidate.cluster_id_b)
        and candidate.cluster_id_a != candidate.cluster_id_b
        and candidate.similarity_score >= candidate_threshold
        and bool(candidate.title_a.strip())
        and bool(candidate.title_b.strip())
        and bool(candidate.merge_reason_zh.strip())
    )


def _candidate_pairs(
    clusters: list[DemandCluster],
    config: dict[str, Any],
) -> list[tuple[DemandCluster, DemandCluster, Any]]:
    threshold = float(config["candidate_threshold"])
    max_per_cluster = int(config["max_candidates_per_cluster"])
    weights = config["fields"]
    scored: list[tuple[DemandCluster, DemandCluster, Any]] = []
    for left, right in combinations(clusters, 2):
        similarity = cluster_merge_similarity(left, right, weights)
        if similarity.total >= threshold:
            scored.append((left, right, similarity))
    scored.sort(key=lambda row: row[2].total, reverse=True)

    selected: list[tuple[DemandCluster, DemandCluster, Any]] = []
    cluster_counts: dict[str, int] = {}
    for left, right, similarity in scored:
        if cluster_counts.get(left.cluster_id, 0) >= max_per_cluster:
            continue
        if cluster_counts.get(right.cluster_id, 0) >= max_per_cluster:
            continue
        selected.append((left, right, similarity))
        cluster_counts[left.cluster_id] = cluster_counts.get(left.cluster_id, 0) + 1
        cluster_counts[right.cluster_id] = cluster_counts.get(right.cluster_id, 0) + 1
    return selected


def _candidate_payload(
    candidate_id: str,
    left: DemandCluster,
    right: DemandCluster,
    similarity: Any,
    config: dict[str, Any],
) -> dict[str, Any]:
    strong_threshold = float(config["strong_candidate_threshold"])
    strength = "strong" if similarity.total >= strong_threshold else "medium"
    max_reason_chars = int(config.get("output", {}).get("max_reason_chars", 300))
    return {
        "merge_candidate_id": candidate_id,
        "cluster_id_a": left.cluster_id,
        "cluster_id_b": right.cluster_id,
        "title_a": left.cluster_title_zh,
        "title_b": right.cluster_title_zh,
        "similarity_score": similarity.total,
        "strength": strength,
        "field_scores": similarity.field_scores,
        "shared_personas": similarity.shared_personas,
        "shared_domain_tags": similarity.shared_domain_tags,
        "shared_keywords": similarity.shared_keywords,
        "merge_reason_zh": _merge_reason(left, right, similarity, max_reason_chars),
        "risk_note_zh": _risk_note(similarity),
        "representative_quotes_a": left.representative_quotes[:3],
        "representative_quotes_b": right.representative_quotes[:3],
    }


def _merge_reason(
    left: DemandCluster,
    right: DemandCluster,
    similarity: Any,
    max_chars: int,
) -> str:
    parts: list[str] = []
    if similarity.shared_keywords:
        parts.append(f"核心痛点都涉及「{'、'.join(similarity.shared_keywords[:4])}」")
    if similarity.shared_personas:
        parts.append(f"目标用户都有{_label_values(similarity.shared_personas, PERSONA_ZH)}")
    if similarity.shared_domain_tags:
        parts.append(f"相关领域都包含{_label_values(similarity.shared_domain_tags, DOMAIN_ZH)}")
    if similarity.field_scores.get("workaround_similarity", 0) >= 55:
        parts.append("当前替代方案也较相似")
    if not parts:
        parts.append("标题、摘要和代表性痛点存在文本相似")
    reason = (
        f"这两个需求主题的{('，且'.join(parts))}，综合相似度为{similarity.total:.1f}。"
        "建议人工检查是否可合并为同一类需求。"
    )
    return reason[:max_chars]


def _risk_note(similarity: Any) -> str | None:
    risks: list[str] = []
    if not similarity.shared_personas:
        risks.append("目标用户不完全一致")
    if not similarity.shared_domain_tags:
        risks.append("领域标签不完全一致")
    if similarity.field_scores.get("pain_description_similarity", 0) < 60:
        risks.append("代表性痛点相似度不高")
    if not risks:
        return None
    return "需要注意：" + "，".join(risks) + "。"


def _label_values(values: list[str], labels: dict[str, str]) -> str:
    return "、".join(labels.get(value, value) for value in values)


def _load_merge_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        return DEFAULT_MERGE_SUGGESTION_CONFIG
    raw = load_yaml(config_path).get("merge_suggestion") or {}
    if not isinstance(raw, dict):
        return DEFAULT_MERGE_SUGGESTION_CONFIG
    merged = {**DEFAULT_MERGE_SUGGESTION_CONFIG, **raw}
    merged["fields"] = {**DEFAULT_MERGE_WEIGHTS, **(raw.get("fields") or {})}
    merged["output"] = {**DEFAULT_MERGE_SUGGESTION_CONFIG["output"], **(raw.get("output") or {})}
    return merged
