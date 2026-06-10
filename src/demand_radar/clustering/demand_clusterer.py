"""Rule-based Demand Clustering Loop for Stage 2."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from demand_radar.clustering.cluster_schema import DemandCluster
from demand_radar.clustering.cluster_store import write_demand_clusters
from demand_radar.clustering.similarity import DEFAULT_WEIGHTS, pain_point_similarity
from demand_radar.config.load_config import load_yaml
from demand_radar.config.schemas import PainPoint
from demand_radar.state.processed_store import load_pain_points
from demand_radar.state.raw_store import next_ids, write_jsonl
from demand_radar.ui.chinese_presenter import build_chinese_review_view
from demand_radar.ui.review_service import ReviewItem


DEFAULT_CLUSTERING_CONFIG = {
    "enabled": True,
    "similarity_threshold": 70,
    "singleton_clusters": True,
    "max_representative_quotes": 3,
    "fields": DEFAULT_WEIGHTS,
    "cluster_title": {"language": "zh", "max_chars": 80},
}

PERSONA_ZH = {
    "investor": "投资人",
    "researcher": "研究员",
    "founder": "创始人",
    "content_team": "内容团队",
    "developer": "开发者",
    "operator": "运营",
    "strategy_bd": "战略与商务拓展团队",
}

WORKFLOW_ZH = {
    "ai_investment_research": "人工智能产业跟踪",
    "content_production": "内容选题生产",
    "ai_agent_workflow": "人工智能智能体工作流",
    "enterprise_knowledge_workflow": "企业知识工作流",
    "developer_workflow": "开发者工具链",
    "general_workflow": "相关工作流",
}

PAIN_PHRASES = [
    ("信息分散", ["scattered", "分散", "信息太乱"]),
    ("难验证", ["verify", "验证", "核对"]),
    ("人工整理低效", ["manual", "人工", "spreadsheet", "表格"]),
    ("容易遗漏", ["miss", "遗漏", "漏"]),
    ("噪音过多", ["noisy", "噪音", "太乱"]),
    ("检索困难", ["find", "search", "查找", "搜索", "筛选"]),
    ("总结困难", ["summarize", "summary", "总结", "摘要"]),
    ("流程不可靠", ["not reliable", "broken", "handoff", "不可靠", "不好追踪"]),
    ("文档不完整", ["docs", "incomplete", "文档", "不完整"]),
    ("耗时过多", ["too much time", "waste", "耗时", "费时间"]),
]


def run_demand_clustering(
    pain_points_path: str | Path = "data/processed/pain_points.jsonl",
    clusters_path: str | Path = "data/processed/demand_clusters.jsonl",
    invalid_clusters_path: str | Path = "data/quarantine/invalid_clusters.jsonl",
    config_path: str | Path = "configs/clustering_config.yaml",
) -> list[DemandCluster]:
    config = _load_clustering_config(config_path)
    pain_points = load_pain_points(pain_points_path)
    groups = _cluster_pain_points(pain_points, config)
    cluster_ids = next_ids("cluster", [], len(groups))
    clusters: list[DemandCluster] = []
    invalid_rows: list[dict[str, Any]] = []

    for cluster_id, group in zip(cluster_ids, groups, strict=True):
        try:
            cluster = _build_cluster(cluster_id, group, config)
        except (ValidationError, ValueError) as exc:
            invalid_rows.append(
                {
                    "cluster_id": cluster_id,
                    "reason": "cluster_invalid",
                    "errors": str(exc),
                    "pain_point_ids": [pain.pain_point_id for pain in group],
                }
            )
            continue
        if not cluster_gate(cluster):
            invalid_rows.append(
                {
                    "cluster_id": cluster.cluster_id,
                    "reason": "cluster_gate_failed",
                    "cluster": cluster.model_dump(mode="json"),
                }
            )
            continue
        clusters.append(cluster)

    write_demand_clusters(clusters, clusters_path)
    write_jsonl(invalid_clusters_path, invalid_rows)
    return clusters


def cluster_gate(cluster: DemandCluster) -> bool:
    return (
        bool(cluster.related_pain_point_ids)
        and bool(cluster.cluster_title_zh.strip())
        and bool(cluster.cluster_summary_zh.strip())
        and cluster.evidence_count >= 1
        and cluster.cluster_confidence >= 0.5
    )


def _cluster_pain_points(
    pain_points: list[PainPoint],
    config: dict[str, Any],
) -> list[list[PainPoint]]:
    threshold = float(config["similarity_threshold"])
    weights = config["fields"]
    groups: list[list[PainPoint]] = []
    for pain_point in pain_points:
        best_index: int | None = None
        best_score = 0.0
        for index, group in enumerate(groups):
            group_score = max(
                pain_point_similarity(pain_point, existing, weights).total for existing in group
            )
            if group_score > best_score:
                best_score = group_score
                best_index = index
        if best_index is not None and best_score >= threshold:
            groups[best_index].append(pain_point)
        else:
            groups.append([pain_point])
    return groups


def _build_cluster(
    cluster_id: str,
    group: list[PainPoint],
    config: dict[str, Any],
) -> DemandCluster:
    personas = _unique_non_empty(pain.persona for pain in group)
    workflow_family = _workflow_family(group)
    domain_tags = [workflow_family] if workflow_family != "general_workflow" else []
    max_quotes = int(config["max_representative_quotes"])
    confidence = _cluster_confidence(group)
    title = _cluster_title(personas, workflow_family, group)
    summary = _cluster_summary(personas, workflow_family, group)
    expected_quality_mix = Counter(
        quality for pain in group if (quality := _batch_value(pain.expected_quality))
    )
    return DemandCluster(
        cluster_id=cluster_id,
        cluster_title_zh=title,
        cluster_summary_zh=summary,
        personas=personas,
        domain_tags=domain_tags,
        workflow_family=workflow_family,
        batch_ids=_unique_non_empty(_batch_id(pain.batch_id) for pain in group),
        signal_focuses=_unique_non_empty(pain.signal_focus for pain in group),
        expected_quality_mix=dict(expected_quality_mix),
        related_pain_point_ids=[pain.pain_point_id for pain in group],
        evidence_count=len(group),
        source_count=len({pain.raw_signal_id for pain in group}),
        representative_pain_descriptions=_unique_non_empty(
            _zh_from_pain(pain, "pain_description") for pain in group
        )[:max_quotes],
        representative_quotes=_unique_non_empty(_zh_from_pain(pain, "evidence_quote") for pain in group)[
            :max_quotes
        ],
        current_workarounds=_unique_non_empty(_zh_from_pain(pain, "current_workaround") for pain in group)[
            :max_quotes
        ],
        cluster_confidence=confidence,
        cluster_method="rule_similarity_v1",
    )


def _cluster_title(personas: list[str], workflow_family: str, group: list[PainPoint]) -> str:
    persona_text = "、".join(PERSONA_ZH.get(persona, persona) for persona in personas) or "相关用户"
    workflow_text = WORKFLOW_ZH.get(workflow_family, "相关工作流")
    pain_text = "、".join(_core_pain_phrases(group)[:3]) or "需求不清晰"
    return f"{persona_text}在{workflow_text}中遇到的「{pain_text}」问题"


def _cluster_summary(personas: list[str], workflow_family: str, group: list[PainPoint]) -> str:
    persona_text = "、".join(PERSONA_ZH.get(persona, persona) for persona in personas) or "相关用户"
    workflow_text = WORKFLOW_ZH.get(workflow_family, "相关工作流")
    pains = "、".join(_core_pain_phrases(group)[:4]) or "痛点仍需人工确认"
    evidence_count = len(group)
    workaround = "、".join(
        _unique_non_empty(_zh_from_pain(pain, "current_workaround") for pain in group)[:2]
    )
    suffix = f"当前多依赖{workaround}。" if workaround else "当前替代方案仍需继续确认。"
    return f"{persona_text}在{workflow_text}中反复出现{pains}等问题，共有{evidence_count}条痛点证据。{suffix}"


def _core_pain_phrases(group: list[PainPoint]) -> list[str]:
    parts: list[str] = []
    for pain in group:
        parts.extend(
            [
                pain.pain_description,
                pain.scenario or "",
                pain.job_to_be_done or "",
                pain.current_workaround or "",
                pain.evidence_quote,
            ]
        )
    text = " ".join(parts).lower()
    phrases: list[str] = []
    for phrase, keywords in PAIN_PHRASES:
        if any(keyword.lower() in text for keyword in keywords):
            phrases.append(phrase)
    return phrases


def _cluster_confidence(group: list[PainPoint]) -> float:
    if len(group) == 1:
        return 0.55
    avg_pain_confidence = sum(pain.confidence for pain in group) / len(group)
    diversity_bonus = 0.05 if len({pain.raw_signal_id for pain in group}) > 1 else 0
    size_bonus = min(0.15, 0.03 * (len(group) - 1))
    return round(min(0.95, avg_pain_confidence + diversity_bonus + size_bonus), 2)


def _workflow_family(group: list[PainPoint]) -> str:
    parts: list[str] = []
    for pain in group:
        parts.extend(
            [
                pain.persona or "",
                pain.scenario or "",
                pain.job_to_be_done or "",
                pain.pain_description,
                pain.evidence_quote,
            ]
        )
    blob = " ".join(parts).lower()
    if any(word in blob for word in ["invest", "vc", "fund", "投资", "尽调"]):
        return "ai_investment_research"
    if any(word in blob for word in ["content", "newsletter", "creator", "内容", "选题"]):
        return "content_production"
    if any(word in blob for word in ["agent", "handoff", "browser", "智能体"]):
        return "ai_agent_workflow"
    if any(word in blob for word in ["developer", "api", "sdk", "github", "开发者", "接口"]):
        return "developer_workflow"
    if any(word in blob for word in ["knowledge", "sop", "operator", "crm", "企业", "知识库", "运营"]):
        return "enterprise_knowledge_workflow"
    return "general_workflow"


def _zh_from_pain(pain: PainPoint, field: str) -> str:
    value = getattr(pain, field) or ""
    item = ReviewItem(
        raw_signal_id=pain.raw_signal_id,
        normalized_signal_id=pain.normalized_signal_id,
        pain_point_id=pain.pain_point_id,
        item_type="pain_point",
        title=pain.scenario or pain.pain_description,
        pain_description=pain.pain_description,
        persona=pain.persona,
        scenario=pain.scenario,
        job_to_be_done=pain.job_to_be_done,
        current_workaround=pain.current_workaround,
        frequency_signal=pain.frequency_signal,
        payment_signal=pain.payment_signal,
        confidence=pain.confidence,
        evidence_quote=pain.evidence_quote,
        domain_tags=[],
    )
    view = build_chinese_review_view(item)
    mapping = {
        "pain_description": view.pain_description,
        "evidence_quote": view.evidence_summary,
        "current_workaround": view.current_workaround,
    }
    return mapping.get(field, value)


def _unique_non_empty(values: Any) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in result:
            result.append(text)
    return result


def _batch_id(value: str | None) -> str:
    return _batch_value(value) or "default"


def _batch_value(value: str | None) -> str:
    return str(value or "").strip()


def _load_clustering_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        return DEFAULT_CLUSTERING_CONFIG
    raw = load_yaml(config_path).get("clustering") or {}
    if not isinstance(raw, dict):
        return DEFAULT_CLUSTERING_CONFIG
    merged = {**DEFAULT_CLUSTERING_CONFIG, **raw}
    fields = {**DEFAULT_WEIGHTS, **(raw.get("fields") or {})}
    merged["fields"] = fields
    return merged
