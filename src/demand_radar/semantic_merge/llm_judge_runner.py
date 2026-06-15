"""LLM semantic merge judge runner for Stage 2.9.

Reads merge candidates and clusters, calls the configured LLM client,
and writes results to llm_* paths that are separate from rule_based outputs.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from demand_radar.clustering.cluster_schema import DemandCluster
from demand_radar.clustering.cluster_store import load_demand_clusters
from demand_radar.clustering.merge_schema import ClusterMergeCandidate
from demand_radar.clustering.merge_store import load_merge_candidates
from demand_radar.config.load_config import load_yaml
from demand_radar.semantic_merge.exception_queue import (
    config_from_dict,
    determine_auto_action,
)
from demand_radar.semantic_merge.llm_cache import LLMSemanticMergeCache
from demand_radar.semantic_merge.llm_client import BaseLLMClient, FakeLLMClient, make_llm_client
from demand_radar.semantic_merge.llm_output_parser import LLMParseError, parse_llm_output
from demand_radar.semantic_merge.semantic_merge_schema import SemanticMergeJudgment
from demand_radar.semantic_merge.semantic_merge_store import (
    build_human_exception_queue,
    write_human_exception_items,
    write_semantic_merge_judgments,
)
from demand_radar.state.raw_store import next_ids


DEFAULT_LLM_JUDGMENTS_PATH = Path("data/processed/llm_semantic_merge_judgments.jsonl")
DEFAULT_LLM_EXCEPTIONS_PATH = Path("data/processed/llm_human_exception_queue.jsonl")
DEFAULT_LLM_GROUPS_PATH = Path("data/processed/llm_ai_reviewed_cluster_groups.jsonl")


def _build_system_prompt(prompt_path: str | Path = "prompts/semantic_merge_judge.md") -> str:
    path = Path(prompt_path)
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    # Minimal inline fallback
    return (
        "You are a demand-cluster merge judge. "
        "Output only a JSON object with keys: decision, confidence, reason_zh, "
        "evidence_alignment_zh, workflow_judgment_zh, suggested_group_title_zh, "
        "suggested_group_summary_zh, conflict_flags. "
        "decision must be confirm_merge, reject_merge, or maybe_merge."
    )


def _build_user_prompt(
    candidate: ClusterMergeCandidate,
    cluster_a: DemandCluster,
    cluster_b: DemandCluster,
) -> str:
    def _join(values: list[str]) -> str:
        return "、".join(v for v in values if v) or "无"

    def _score_str(scores: dict[str, float]) -> str:
        return "；".join(f"{k}={v:.1f}" for k, v in scores.items()) or "无"

    return (
        f"merge_candidate_id: {candidate.merge_candidate_id}\n"
        f"similarity_score: {candidate.similarity_score:.1f}\n"
        f"field_scores: {_score_str(candidate.field_scores)}\n"
        f"shared_personas: {_join(candidate.shared_personas)}\n"
        f"shared_keywords: {_join(candidate.shared_keywords[:6])}\n"
        f"shared_domain_tags: {_join(candidate.shared_domain_tags)}\n\n"
        f"cluster_a:\n"
        f"  cluster_id: {cluster_a.cluster_id}\n"
        f"  cluster_title_zh: {cluster_a.cluster_title_zh}\n"
        f"  cluster_summary_zh: {cluster_a.cluster_summary_zh}\n"
        f"  personas: {_join(cluster_a.personas)}\n"
        f"  domain_tags: {_join(cluster_a.domain_tags)}\n"
        f"  workflow_family: {cluster_a.workflow_family or '未知'}\n"
        f"  representative_pain_descriptions: {_join(cluster_a.representative_pain_descriptions[:2])}\n"
        f"  current_workarounds: {_join(cluster_a.current_workarounds[:2])}\n"
        f"  representative_quotes: {_join(cluster_a.representative_quotes[:2])}\n"
        f"  evidence_count: {cluster_a.evidence_count}\n\n"
        f"cluster_b:\n"
        f"  cluster_id: {cluster_b.cluster_id}\n"
        f"  cluster_title_zh: {cluster_b.cluster_title_zh}\n"
        f"  cluster_summary_zh: {cluster_b.cluster_summary_zh}\n"
        f"  personas: {_join(cluster_b.personas)}\n"
        f"  domain_tags: {_join(cluster_b.domain_tags)}\n"
        f"  workflow_family: {cluster_b.workflow_family or '未知'}\n"
        f"  representative_pain_descriptions: {_join(cluster_b.representative_pain_descriptions[:2])}\n"
        f"  current_workarounds: {_join(cluster_b.current_workarounds[:2])}\n"
        f"  representative_quotes: {_join(cluster_b.representative_quotes[:2])}\n"
        f"  evidence_count: {cluster_b.evidence_count}\n"
    )


def _llm_judgment(
    judgment_id: str,
    candidate: ClusterMergeCandidate,
    cluster_a: DemandCluster,
    cluster_b: DemandCluster,
    client: BaseLLMClient,
    gate_config: Any,
    system_prompt: str,
    cache: LLMSemanticMergeCache,
    model: str,
) -> SemanticMergeJudgment:
    """Call LLM (or cache) and build a SemanticMergeJudgment."""
    cached = cache.get(candidate.merge_candidate_id, candidate.cluster_id_a, candidate.cluster_id_b, model)
    if cached is not None:
        data = cached
    else:
        user_prompt = _build_user_prompt(candidate, cluster_a, cluster_b)
        try:
            raw = client.complete(system_prompt, user_prompt)
            data = parse_llm_output(raw)
            cache.set(candidate.merge_candidate_id, candidate.cluster_id_a, candidate.cluster_id_b, model, data)
        except (LLMParseError, Exception) as exc:
            return _failure_judgment(judgment_id, candidate, str(exc), getattr(client, "provider", "llm"), gate_config)

    try:
        decision = str(data["decision"])
        confidence = float(data["confidence"])
        reason_zh = str(data.get("reason_zh", "")).strip()
        evidence_alignment_zh = str(data.get("evidence_alignment_zh", "")).strip() or None
        workflow_judgment_zh = str(data.get("workflow_judgment_zh", "")).strip() or None
        title = str(data.get("suggested_group_title_zh", "")).strip() or None
        summary_zh = str(data.get("suggested_group_summary_zh", "")).strip() or None
        flags = [str(f).strip() for f in (data.get("conflict_flags") or []) if str(f).strip()]
        auto_action = determine_auto_action(
            decision=decision,
            confidence=confidence,
            conflict_flags=flags,
            suggested_group_title_zh=title,
            suggested_group_summary_zh=summary_zh,
            reason_zh=reason_zh,
            config=gate_config,
            evidence_alignment_zh=evidence_alignment_zh,
            workflow_judgment_zh=workflow_judgment_zh,
        )
        return SemanticMergeJudgment(
            judgment_id=judgment_id,
            merge_candidate_id=candidate.merge_candidate_id,
            cluster_id_a=candidate.cluster_id_a,
            cluster_id_b=candidate.cluster_id_b,
            decision=decision,
            confidence=confidence,
            reason_zh=reason_zh,
            evidence_alignment_zh=evidence_alignment_zh,
            workflow_judgment_zh=workflow_judgment_zh,
            suggested_group_title_zh=title,
            suggested_group_summary_zh=summary_zh,
            conflict_flags=flags,
            auto_action=auto_action,
            judge_mode="llm",
        )
    except Exception as exc:
        return _failure_judgment(judgment_id, candidate, str(exc), "llm", gate_config)


def _failure_judgment(
    judgment_id: str,
    candidate: ClusterMergeCandidate,
    error_detail: str,
    provider: str,
    gate_config: Any,
) -> SemanticMergeJudgment:
    reason = f"LLM调用失败或输出无效，已转入人工异常队列。错误：{error_detail[:120]}"
    auto_action = determine_auto_action(
        decision="maybe_merge",
        confidence=0.0,
        conflict_flags=["weak_evidence"],
        suggested_group_title_zh=None,
        suggested_group_summary_zh=None,
        reason_zh=reason,
        config=gate_config,
    )
    return SemanticMergeJudgment(
        judgment_id=judgment_id,
        merge_candidate_id=candidate.merge_candidate_id,
        cluster_id_a=candidate.cluster_id_a,
        cluster_id_b=candidate.cluster_id_b,
        decision="maybe_merge",
        confidence=0.0,
        reason_zh=reason,
        evidence_alignment_zh="LLM调用失败，无法评估证据对齐。",
        workflow_judgment_zh="LLM调用失败，无法判断工作流关系。",
        conflict_flags=["weak_evidence"],
        auto_action=auto_action,
        judge_mode="llm",
    )


def run_llm_semantic_merge_judge(
    candidates_path: str | Path = "data/processed/cluster_merge_candidates.jsonl",
    clusters_path: str | Path = "data/processed/demand_clusters.jsonl",
    judgments_path: str | Path = DEFAULT_LLM_JUDGMENTS_PATH,
    exceptions_path: str | Path = DEFAULT_LLM_EXCEPTIONS_PATH,
    config_path: str | Path = "configs/semantic_merge_config.yaml",
    prompt_path: str | Path = "prompts/semantic_merge_judge.md",
    cache_path: str | Path = "data/cache/llm_semantic_merge_cache.jsonl",
    client: BaseLLMClient | None = None,
) -> list[SemanticMergeJudgment]:
    """Run LLM semantic merge judge, writing to llm_* output paths."""
    config = load_yaml(config_path)
    semantic_config = config.get("semantic_merge", {})
    gate_config = config_from_dict(config)
    batch_conf = semantic_config.get("batch", {})
    cache_enabled = bool(batch_conf.get("cache_enabled", True))
    max_candidates = int(batch_conf.get("max_candidates_per_run", 200)) if batch_conf.get("max_candidates_per_run") else None

    if client is None:
        llm_conf = semantic_config.get("llm", {})
        provider = llm_conf.get("provider", "openai_compatible")
        client = make_llm_client(provider, semantic_config)
    model = getattr(client, "model", "fake")
    system_prompt = _build_system_prompt(prompt_path)
    cache = LLMSemanticMergeCache(path=cache_path, enabled=cache_enabled)

    candidates = load_merge_candidates(candidates_path)
    if max_candidates:
        candidates = candidates[:max_candidates]
    clusters = load_demand_clusters(clusters_path)
    cluster_by_id = {c.cluster_id: c for c in clusters}
    judgment_ids = next_ids("llm_semantic_merge_judgment", [], len(candidates))

    judgments: list[SemanticMergeJudgment] = []
    for judgment_id, candidate in zip(judgment_ids, candidates, strict=True):
        cluster_a = cluster_by_id.get(candidate.cluster_id_a)
        cluster_b = cluster_by_id.get(candidate.cluster_id_b)
        if cluster_a is None or cluster_b is None:
            reason = "合并候选引用的需求主题不存在，需要人工检查数据状态。"
            auto_action = determine_auto_action(
                decision="maybe_merge", confidence=0.0, conflict_flags=["weak_evidence"],
                suggested_group_title_zh=None, suggested_group_summary_zh=None,
                reason_zh=reason, config=gate_config,
            )
            judgments.append(SemanticMergeJudgment(
                judgment_id=judgment_id, merge_candidate_id=candidate.merge_candidate_id,
                cluster_id_a=candidate.cluster_id_a, cluster_id_b=candidate.cluster_id_b,
                decision="maybe_merge", confidence=0.0, reason_zh=reason,
                evidence_alignment_zh="缺少可对齐的需求主题证据。",
                workflow_judgment_zh="无法判断工作流关系。",
                conflict_flags=["weak_evidence"], auto_action=auto_action, judge_mode="llm",
            ))
        else:
            judgments.append(_llm_judgment(
                judgment_id, candidate, cluster_a, cluster_b,
                client, gate_config, system_prompt, cache, model,
            ))

    write_semantic_merge_judgments(judgments, judgments_path)
    exceptions = build_human_exception_queue(judgments)
    write_human_exception_items(exceptions, exceptions_path)
    return judgments


def build_llm_ai_reviewed_cluster_groups(
    clusters_path: str | Path = "data/processed/demand_clusters.jsonl",
    judgments_path: str | Path = DEFAULT_LLM_JUDGMENTS_PATH,
    groups_path: str | Path = DEFAULT_LLM_GROUPS_PATH,
    invalid_groups_path: str | Path = "data/quarantine/invalid_llm_ai_reviewed_groups.jsonl",
) -> list:
    """Build AI reviewed cluster groups from LLM judgments, writing to llm_* paths."""
    from demand_radar.semantic_merge.semantic_merge_store import build_ai_reviewed_cluster_groups
    return build_ai_reviewed_cluster_groups(
        clusters_path=clusters_path,
        judgments_path=judgments_path,
        groups_path=groups_path,
        invalid_groups_path=invalid_groups_path,
    )
