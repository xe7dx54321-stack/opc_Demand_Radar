"""Semantic merge judge implementations for Stage 2.8."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Protocol

from demand_radar.clustering.cluster_schema import DemandCluster
from demand_radar.clustering.cluster_store import load_demand_clusters
from demand_radar.clustering.merge_schema import ClusterMergeCandidate
from demand_radar.clustering.merge_store import load_merge_candidates
from demand_radar.config.load_config import load_yaml
from demand_radar.semantic_merge.exception_queue import (
    config_from_dict,
    determine_auto_action,
)
from demand_radar.semantic_merge.semantic_merge_schema import SemanticMergeJudgment
from demand_radar.semantic_merge.semantic_merge_store import (
    build_human_exception_queue,
    write_human_exception_items,
    write_semantic_merge_judgments,
)
from demand_radar.state.raw_store import next_ids


class BaseSemanticMergeJudge(Protocol):
    judge_mode: str

    def judge(
        self,
        candidate: ClusterMergeCandidate,
        cluster_a: DemandCluster,
        cluster_b: DemandCluster,
        context: dict[str, Any],
    ) -> SemanticMergeJudgment:
        ...


class RuleBasedSemanticMergeJudge:
    """Offline semantic-merge stub that does not call external services."""

    judge_mode = "rule_based_stub"

    def judge(
        self,
        candidate: ClusterMergeCandidate,
        cluster_a: DemandCluster,
        cluster_b: DemandCluster,
        context: dict[str, Any],
    ) -> SemanticMergeJudgment:
        gate_config = config_from_dict(context.get("config", {}))
        judgment_id = str(context.get("judgment_id") or "")
        decision, confidence, conflict_flags = self._decision(candidate, cluster_a, cluster_b)
        title = _suggest_group_title(candidate, cluster_a, cluster_b) if decision == "confirm_merge" else None
        summary = _suggest_group_summary(cluster_a, cluster_b) if decision == "confirm_merge" else None
        reason = _reason_zh(decision, candidate, cluster_a, cluster_b, conflict_flags)
        evidence_alignment = _evidence_alignment_zh(candidate, cluster_a, cluster_b)
        workflow_judgment = _workflow_judgment_zh(decision, cluster_a, cluster_b)
        auto_action = determine_auto_action(
            decision=decision,
            confidence=confidence,
            conflict_flags=conflict_flags,
            suggested_group_title_zh=title,
            suggested_group_summary_zh=summary,
            reason_zh=reason,
            config=gate_config,
        )
        return SemanticMergeJudgment(
            judgment_id=judgment_id,
            merge_candidate_id=candidate.merge_candidate_id,
            cluster_id_a=candidate.cluster_id_a,
            cluster_id_b=candidate.cluster_id_b,
            decision=decision,
            confidence=confidence,
            reason_zh=reason,
            evidence_alignment_zh=evidence_alignment,
            workflow_judgment_zh=workflow_judgment,
            suggested_group_title_zh=title,
            suggested_group_summary_zh=summary,
            conflict_flags=conflict_flags,
            auto_action=auto_action,
            judge_mode=self.judge_mode,
        )

    def _decision(
        self,
        candidate: ClusterMergeCandidate,
        cluster_a: DemandCluster,
        cluster_b: DemandCluster,
    ) -> tuple[str, float, list[str]]:
        field_scores = candidate.field_scores
        pain_score = float(field_scores.get("pain_description_similarity", 0))
        summary_score = float(field_scores.get("summary_similarity", 0))
        workaround_score = float(field_scores.get("workaround_similarity", 0))
        persona_overlap = bool(set(cluster_a.personas) & set(cluster_b.personas)) or bool(candidate.shared_personas)
        domain_overlap = bool(set(cluster_a.domain_tags) & set(cluster_b.domain_tags)) or bool(candidate.shared_domain_tags)
        workflow_same = bool(cluster_a.workflow_family and cluster_a.workflow_family == cluster_b.workflow_family)
        conflict_flags = _conflict_flags(candidate, cluster_a, cluster_b)

        if (
            candidate.similarity_score >= 82
            and pain_score >= 75
            and summary_score >= 70
            and (persona_overlap or domain_overlap or workflow_same)
            and not (set(conflict_flags) & {"different_persona", "different_workflow", "different_pain"})
        ):
            confidence = min(0.9, 0.86 + (candidate.similarity_score - 82) / 200)
            return "confirm_merge", round(confidence, 2), []

        if (
            candidate.similarity_score <= 60
            or pain_score < 50
            or ("different_workflow" in conflict_flags and "different_persona" in conflict_flags)
        ):
            confidence = 0.88 if candidate.similarity_score <= 55 or pain_score < 45 else 0.86
            return "reject_merge", confidence, conflict_flags or ["different_pain"]

        confidence = 0.60 + (candidate.similarity_score - 60) / 200
        maybe_flags = [flag for flag in conflict_flags if flag in {"ambiguous_scope", "weak_evidence", "title_mismatch"}]
        return "maybe_merge", round(min(0.79, confidence), 2), maybe_flags


# ---------------------------------------------------------------------------
# LLM judge (real structured output)
# ---------------------------------------------------------------------------

_LLM_SYSTEM_PROMPT = """你是需求合并分析专家。你的任务是判断两个需求主题（demand cluster）是否应该合并成一个更高层级的需求组。

输出必须是 JSON，结构如下：
{
  "decision": "confirm_merge | reject_merge | maybe_merge",
  "confidence": 0.0,
  "reason_zh": "（必须中文）",
  "evidence_alignment_zh": "（必须中文）",
  "workflow_judgment_zh": "（必须中文）",
  "suggested_group_title_zh": "（confirm_merge 时必填，其他时可为空字符串）",
  "suggested_group_summary_zh": "（confirm_merge 时必填，其他时可为空字符串）",
  "conflict_flags": []
}

规则：
1. 不允许引入输入文本以外的外部事实。
2. 不允许为了减少 cluster 数量而强行合并。
3. 两个需求只是关键词相似，但工作流不同，必须 reject_merge。
4. 如果证据不足或层级不一致，必须 maybe_merge。
5. confirm_merge 必须给出 suggested_group_title_zh 和 suggested_group_summary_zh。
6. 所有中文字段必须是中文内容。
7. confidence 必须在 0.0 到 1.0 之间。
8. conflict_flags 只能包含：different_persona、different_workflow、different_pain、weak_evidence、ambiguous_scope、too_broad、too_narrow、title_mismatch"""

_LLM_USER_TEMPLATE = """请判断以下两个需求主题是否应该合并：

## 主题甲（Cluster A）
- 标题：{title_a}
- 摘要：{summary_a}
- 目标用户：{personas_a}
- 领域标签：{domain_a}
- 工作流族：{workflow_a}
- 代表性痛点：{pain_a}
- 代表性引用：{quotes_a}
- 当前替代方案：{workarounds_a}
- 证据数量：{evidence_a}

## 主题乙（Cluster B）
- 标题：{title_b}
- 摘要：{summary_b}
- 目标用户：{personas_b}
- 领域标签：{domain_b}
- 工作流族：{workflow_b}
- 代表性痛点：{pain_b}
- 代表性引用：{quotes_b}
- 当前替代方案：{workarounds_b}
- 证据数量：{evidence_b}

## 候选信息
- 整体相似度分数：{similarity_score}
- 共享用户角色：{shared_personas}
- 共享关键词：{shared_keywords}
- 共享领域标签：{shared_domains}
- 字段相似度明细：{field_scores}"""


def _build_user_prompt(
    candidate: ClusterMergeCandidate,
    cluster_a: DemandCluster,
    cluster_b: DemandCluster,
) -> str:
    def _join(values: list[str]) -> str:
        return "、".join(values) if values else "无"

    def _score_str(scores: dict[str, float]) -> str:
        return "；".join(f"{key}={value:.1f}" for key, value in scores.items())

    return _LLM_USER_TEMPLATE.format(
        title_a=cluster_a.cluster_title_zh,
        summary_a=cluster_a.cluster_summary_zh,
        personas_a=_join(cluster_a.personas),
        domain_a=_join(cluster_a.domain_tags),
        workflow_a=cluster_a.workflow_family or "未知",
        pain_a=_join(cluster_a.representative_pain_descriptions[:2]),
        quotes_a=_join(cluster_a.representative_quotes[:2]),
        workarounds_a=_join(cluster_a.current_workarounds[:2]),
        evidence_a=cluster_a.evidence_count,
        title_b=cluster_b.cluster_title_zh,
        summary_b=cluster_b.cluster_summary_zh,
        personas_b=_join(cluster_b.personas),
        domain_b=_join(cluster_b.domain_tags),
        workflow_b=cluster_b.workflow_family or "未知",
        pain_b=_join(cluster_b.representative_pain_descriptions[:2]),
        quotes_b=_join(cluster_b.representative_quotes[:2]),
        workarounds_b=_join(cluster_b.current_workarounds[:2]),
        evidence_b=cluster_b.evidence_count,
        similarity_score=candidate.similarity_score,
        shared_personas=_join(candidate.shared_personas),
        shared_keywords=_join(candidate.shared_keywords[:5]),
        shared_domains=_join(candidate.shared_domain_tags),
        field_scores=_score_str(candidate.field_scores),
    )


def _parse_llm_response(raw: str) -> dict[str, Any]:
    """Extract JSON from LLM response text, tolerating markdown fences."""
    text = raw.strip()
    for fence in ("```json", "```"):
        if text.startswith(fence):
            text = text[len(fence):]
    if text.endswith("```"):
        text = text[:-3]
    return json.loads(text.strip())


class LLMSemanticMergeJudge:
    """Real LLM structured-output judge using an OpenAI-compatible API.

    Falls back to human_exception on any failure without raising.
    """

    judge_mode = "llm"

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: int = 60,
        max_retries: int = 2,
        temperature: float = 0.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.temperature = temperature

    @classmethod
    def from_config(cls, semantic_config: dict[str, Any]) -> "LLMSemanticMergeJudge":
        llm_conf = semantic_config.get("llm", {})
        base_url = os.environ.get(llm_conf.get("base_url_env", "DEMAND_RADAR_LLM_BASE_URL"), "")
        api_key = os.environ.get(llm_conf.get("api_key_env", "DEMAND_RADAR_LLM_API_KEY"), "")
        model = llm_conf.get("model", "")
        timeout_seconds = int(llm_conf.get("timeout_seconds", 60))
        max_retries = int(llm_conf.get("max_retries", 2))
        temperature = float(llm_conf.get("temperature", 0.0))
        return cls(
            base_url=base_url,
            api_key=api_key,
            model=model,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            temperature=temperature,
        )

    def _call_api(self, user_prompt: str) -> dict[str, Any]:
        payload = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": _LLM_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.temperature,
        }).encode("utf-8")
        url = f"{self.base_url}/chat/completions"
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        last_error: Exception | None = None
        for _ in range(self.max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                    return _parse_llm_response(body["choices"][0]["message"]["content"])
            except Exception as exc:
                last_error = exc
        raise RuntimeError(f"LLM API call failed after {self.max_retries + 1} attempts: {last_error}")

    def judge(
        self,
        candidate: ClusterMergeCandidate,
        cluster_a: DemandCluster,
        cluster_b: DemandCluster,
        context: dict[str, Any],
    ) -> SemanticMergeJudgment:
        gate_config = config_from_dict(context.get("config", {}))
        judgment_id = str(context.get("judgment_id") or "")
        user_prompt = _build_user_prompt(candidate, cluster_a, cluster_b)
        try:
            raw = self._call_api(user_prompt)
            decision = str(raw.get("decision", "")).strip()
            confidence = float(raw.get("confidence", 0.0))
            reason_zh = str(raw.get("reason_zh", "")).strip()
            evidence_alignment_zh = str(raw.get("evidence_alignment_zh", "")).strip() or None
            workflow_judgment_zh = str(raw.get("workflow_judgment_zh", "")).strip() or None
            suggested_group_title_zh = str(raw.get("suggested_group_title_zh", "")).strip() or None
            suggested_group_summary_zh = str(raw.get("suggested_group_summary_zh", "")).strip() or None
            raw_flags = raw.get("conflict_flags", [])
            conflict_flags = [str(flag).strip() for flag in raw_flags if str(flag).strip()]
            if decision not in ("confirm_merge", "reject_merge", "maybe_merge"):
                raise ValueError(f"invalid LLM decision: {decision!r}")
            if not reason_zh or not any("\u4e00" <= char <= "\u9fff" for char in reason_zh):
                raise ValueError("reason_zh missing or not Chinese")
        except Exception:
            reason_fallback = "LLM调用失败或返回格式无效，已转入人工异常队列。"
            auto_action = determine_auto_action(
                decision="maybe_merge",
                confidence=0.0,
                conflict_flags=["weak_evidence"],
                suggested_group_title_zh=None,
                suggested_group_summary_zh=None,
                reason_zh=reason_fallback,
                config=gate_config,
            )
            return SemanticMergeJudgment(
                judgment_id=judgment_id,
                merge_candidate_id=candidate.merge_candidate_id,
                cluster_id_a=candidate.cluster_id_a,
                cluster_id_b=candidate.cluster_id_b,
                decision="maybe_merge",
                confidence=0.0,
                reason_zh=reason_fallback,
                evidence_alignment_zh="LLM调用失败，无法评估证据对齐。",
                workflow_judgment_zh="LLM调用失败，无法判断工作流。",
                conflict_flags=["weak_evidence"],
                auto_action=auto_action,
                judge_mode=self.judge_mode,
            )

        auto_action = determine_auto_action(
            decision=decision,
            confidence=confidence,
            conflict_flags=conflict_flags,
            suggested_group_title_zh=suggested_group_title_zh,
            suggested_group_summary_zh=suggested_group_summary_zh,
            reason_zh=reason_zh,
            config=gate_config,
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
            suggested_group_title_zh=suggested_group_title_zh,
            suggested_group_summary_zh=suggested_group_summary_zh,
            conflict_flags=conflict_flags,
            auto_action=auto_action,
            judge_mode=self.judge_mode,
        )


class FakeLLMJudge:
    """Controllable fake LLM judge for unit tests.  Does not call any API."""

    judge_mode = "llm"

    def __init__(self, responses: list[dict[str, Any]] | None = None) -> None:
        self._responses = list(responses or [])
        self._call_count = 0

    def judge(
        self,
        candidate: ClusterMergeCandidate,
        cluster_a: DemandCluster,
        cluster_b: DemandCluster,
        context: dict[str, Any],
    ) -> SemanticMergeJudgment:
        gate_config = config_from_dict(context.get("config", {}))
        judgment_id = str(context.get("judgment_id") or "")
        idx = min(self._call_count, len(self._responses) - 1) if self._responses else -1
        self._call_count += 1
        if idx < 0:
            raw: dict[str, Any] = {}
        else:
            raw = self._responses[idx]

        decision = str(raw.get("decision", "maybe_merge")).strip()
        if decision not in ("confirm_merge", "reject_merge", "maybe_merge"):
            decision = "maybe_merge"
        confidence = float(raw.get("confidence", 0.0))
        reason_zh = str(raw.get("reason_zh", "测试判断理由")).strip()
        if not any("\u4e00" <= char <= "\u9fff" for char in reason_zh):
            reason_zh = "测试判断理由（中文占位）"
        evidence_alignment_zh = str(raw.get("evidence_alignment_zh", "")) or None
        workflow_judgment_zh = str(raw.get("workflow_judgment_zh", "")) or None
        suggested_group_title_zh = str(raw.get("suggested_group_title_zh", "")) or None
        suggested_group_summary_zh = str(raw.get("suggested_group_summary_zh", "")) or None
        raw_flags = raw.get("conflict_flags", [])
        conflict_flags = [str(flag).strip() for flag in raw_flags if str(flag).strip()]

        auto_action = determine_auto_action(
            decision=decision,
            confidence=confidence,
            conflict_flags=conflict_flags,
            suggested_group_title_zh=suggested_group_title_zh,
            suggested_group_summary_zh=suggested_group_summary_zh,
            reason_zh=reason_zh,
            config=gate_config,
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
            suggested_group_title_zh=suggested_group_title_zh,
            suggested_group_summary_zh=suggested_group_summary_zh,
            conflict_flags=conflict_flags,
            auto_action=auto_action,
            judge_mode=self.judge_mode,
        )


# ---------------------------------------------------------------------------
# Legacy stub — keeps "llm" mode from crashing when no real LLM is configured
# ---------------------------------------------------------------------------

class LLMSemanticMergeJudgeStub(RuleBasedSemanticMergeJudge):
    """Fallback stub used when llm mode is selected but no API is configured."""

    judge_mode = "llm"


def _make_judge(semantic_config: dict[str, Any]) -> BaseSemanticMergeJudge:
    """Select the appropriate judge based on config + environment."""
    mode = semantic_config.get("mode", "rule_based_stub")
    if mode == "llm":
        llm_conf = semantic_config.get("llm", {})
        base_url = os.environ.get(llm_conf.get("base_url_env", "DEMAND_RADAR_LLM_BASE_URL"), "")
        api_key = os.environ.get(llm_conf.get("api_key_env", "DEMAND_RADAR_LLM_API_KEY"), "")
        model = llm_conf.get("model", "")
        if base_url and api_key and model:
            return LLMSemanticMergeJudge.from_config(semantic_config)
        return LLMSemanticMergeJudgeStub()
    return RuleBasedSemanticMergeJudge()


def run_semantic_merge_judge(
    candidates_path: str = "data/processed/cluster_merge_candidates.jsonl",
    clusters_path: str = "data/processed/demand_clusters.jsonl",
    judgments_path: str = "data/processed/semantic_merge_judgments.jsonl",
    exceptions_path: str = "data/processed/human_exception_queue.jsonl",
    config_path: str = "configs/semantic_merge_config.yaml",
) -> list[SemanticMergeJudgment]:
    config = load_yaml(config_path)
    semantic_config = config.get("semantic_merge", {})
    judge: BaseSemanticMergeJudge = _make_judge(semantic_config)

    candidates = load_merge_candidates(candidates_path)
    clusters = load_demand_clusters(clusters_path)
    cluster_by_id = {cluster.cluster_id: cluster for cluster in clusters}
    judgment_ids = next_ids("semantic_merge_judgment", [], len(candidates))
    judgments: list[SemanticMergeJudgment] = []
    for judgment_id, candidate in zip(judgment_ids, candidates, strict=True):
        cluster_a = cluster_by_id.get(candidate.cluster_id_a)
        cluster_b = cluster_by_id.get(candidate.cluster_id_b)
        if cluster_a is None or cluster_b is None:
            judgment = _missing_cluster_judgment(judgment_id, candidate, config, judge_mode=judge.judge_mode)
        else:
            judgment = judge.judge(
                candidate,
                cluster_a,
                cluster_b,
                {"config": config, "judgment_id": judgment_id},
            )
        judgments.append(judgment)

    write_semantic_merge_judgments(judgments, judgments_path)
    exceptions = build_human_exception_queue(judgments)
    write_human_exception_items(exceptions, exceptions_path)
    return judgments


def _missing_cluster_judgment(
    judgment_id: str,
    candidate: ClusterMergeCandidate,
    config: dict,
    judge_mode: str,
) -> SemanticMergeJudgment:
    reason = "合并候选引用的需求主题不存在，无法进行语义合并判断，需要人工检查数据状态。"
    auto_action = determine_auto_action(
        decision="maybe_merge",
        confidence=0.0,
        conflict_flags=["weak_evidence"],
        suggested_group_title_zh=None,
        suggested_group_summary_zh=None,
        reason_zh=reason,
        config=config_from_dict(config),
    )
    return SemanticMergeJudgment(
        judgment_id=judgment_id,
        merge_candidate_id=candidate.merge_candidate_id,
        cluster_id_a=candidate.cluster_id_a,
        cluster_id_b=candidate.cluster_id_b,
        decision="maybe_merge",
        confidence=0.0,
        reason_zh=reason,
        evidence_alignment_zh="缺少可对齐的需求主题证据。",
        workflow_judgment_zh="无法判断两个主题是否属于同一工作流。",
        conflict_flags=["weak_evidence"],
        auto_action=auto_action,
        judge_mode=judge_mode,
    )


# ---------------------------------------------------------------------------
# Helper functions (shared by rule-based and LLM judges)
# ---------------------------------------------------------------------------

def _conflict_flags(
    candidate: ClusterMergeCandidate,
    cluster_a: DemandCluster,
    cluster_b: DemandCluster,
) -> list[str]:
    flags: list[str] = []
    if cluster_a.personas and cluster_b.personas and not set(cluster_a.personas) & set(cluster_b.personas):
        flags.append("different_persona")
    if (
        cluster_a.workflow_family
        and cluster_b.workflow_family
        and cluster_a.workflow_family != cluster_b.workflow_family
    ):
        flags.append("different_workflow")
    if candidate.field_scores.get("pain_description_similarity", 0) < 55:
        flags.append("different_pain")
    if min(cluster_a.evidence_count, cluster_b.evidence_count) <= 1 and candidate.similarity_score < 78:
        flags.append("weak_evidence")
    if candidate.field_scores.get("title_similarity", 0) < 45:
        flags.append("title_mismatch")
    return flags


def _reason_zh(
    decision: str,
    candidate: ClusterMergeCandidate,
    cluster_a: DemandCluster,
    cluster_b: DemandCluster,
    conflict_flags: list[str],
) -> str:
    shared = _shared_text(candidate)
    if decision == "confirm_merge":
        return (
            f"这两个需求主题的核心痛点和工作流高度一致，相似度为 {candidate.similarity_score:.1f}。"
            f"{shared} 因此可以在自动门槛内视为同一类更高层需求。"
        )
    if decision == "reject_merge":
        conflicts = "、".join(_flag_label(flag) for flag in conflict_flags) or "关键语义不一致"
        return (
            f"这两个需求主题虽然进入了候选列表，但存在{conflicts}，"
            "更像是不同用户任务或不同工作流中的问题，不应自动合并。"
        )
    return (
        f"这两个需求主题存在一定相似性，相似度为 {candidate.similarity_score:.1f}，"
        f"{shared} 但证据或范围仍不足以自动确认，建议进入人工异常队列。"
    )


def _evidence_alignment_zh(
    candidate: ClusterMergeCandidate,
    cluster_a: DemandCluster,
    cluster_b: DemandCluster,
) -> str:
    pain_score = candidate.field_scores.get("pain_description_similarity", 0)
    summary_score = candidate.field_scores.get("summary_similarity", 0)
    return (
        f"痛点描述相似度 {pain_score:.1f}，摘要相似度 {summary_score:.1f}。"
        f"主题甲证据 {cluster_a.evidence_count} 条，主题乙证据 {cluster_b.evidence_count} 条。"
    )


def _workflow_judgment_zh(decision: str, cluster_a: DemandCluster, cluster_b: DemandCluster) -> str:
    if cluster_a.workflow_family and cluster_a.workflow_family == cluster_b.workflow_family:
        return f"两个主题都落在 {cluster_a.workflow_family} 工作流下。"
    if decision == "reject_merge":
        return "两个主题的工作流或用户任务不同，不适合合并为同一需求。"
    return "两个主题的工作流存在相似表达，但仍需要人工确认其层级是否一致。"


def _suggest_group_title(
    candidate: ClusterMergeCandidate,
    cluster_a: DemandCluster,
    cluster_b: DemandCluster,
) -> str:
    personas = _unique([*cluster_a.personas, *cluster_b.personas])
    persona_text = _persona_title(personas)
    keywords = candidate.shared_keywords[:2] or _core_terms(cluster_a, cluster_b)
    core = "、".join(keywords) if keywords else "重复人工处理"
    workflow = cluster_a.workflow_family or cluster_b.workflow_family or "相关工作流"
    workflow_text = _workflow_title(workflow)
    return f"{persona_text}在{workflow_text}中遇到的「{core}」问题"


def _suggest_group_summary(cluster_a: DemandCluster, cluster_b: DemandCluster) -> str:
    summaries = _unique([cluster_a.cluster_summary_zh, cluster_b.cluster_summary_zh])
    text = " ".join(summaries)
    return text if len(text) <= 300 else text[:299] + "…"


def _shared_text(candidate: ClusterMergeCandidate) -> str:
    parts: list[str] = []
    if candidate.shared_personas:
        parts.append(f"共享用户角色包括 {'、'.join(candidate.shared_personas)}。")
    if candidate.shared_domain_tags:
        parts.append(f"共享领域包括 {'、'.join(candidate.shared_domain_tags)}。")
    if candidate.shared_keywords:
        parts.append(f"共享关键词包括 {'、'.join(candidate.shared_keywords[:5])}。")
    return "".join(parts) or "当前共享信息较少。"


def _core_terms(cluster_a: DemandCluster, cluster_b: DemandCluster) -> list[str]:
    terms: list[str] = []
    for text in [*cluster_a.representative_pain_descriptions, *cluster_b.representative_pain_descriptions]:
        for token in ["信息分散", "人工整理", "难验证", "噪音过多", "重复处理", "上下文丢失", "搜索困难"]:
            if token in text and token not in terms:
                terms.append(token)
    return terms[:2]


def _persona_title(personas: list[str]) -> str:
    labels = {
        "investor": "投资人",
        "researcher": "研究员",
        "founder": "创始人",
        "content_team": "内容团队",
        "developer": "开发者",
        "operator": "运营人员",
        "strategy_bd": "战略与商务拓展",
    }
    translated = [labels.get(persona, persona) for persona in personas if persona]
    return "、".join(translated[:2]) if translated else "相关用户"


def _workflow_title(value: str) -> str:
    labels = {
        "ai_investment_research": "AI 产业研究",
        "content_production": "内容选题生产",
        "enterprise_knowledge_workflow": "企业知识工作流",
        "ai_agent_workflow": "智能体工作流",
        "developer_workflow": "开发者工具链",
        "general_workflow": "相关工作流",
    }
    return labels.get(value, value)


def _flag_label(flag: str) -> str:
    labels = {
        "different_persona": "用户角色不同",
        "different_workflow": "工作流不同",
        "different_pain": "核心痛点不同",
        "weak_evidence": "证据偏弱",
        "ambiguous_scope": "范围不清",
        "too_broad": "范围过宽",
        "too_narrow": "范围过窄",
        "title_mismatch": "标题语义不匹配",
    }
    return labels.get(flag, flag)


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in result:
            result.append(text)
    return result
