"""Confidence gate and exception queue helpers for semantic merge judgments."""

from __future__ import annotations

from dataclasses import dataclass, field

from demand_radar.semantic_merge.semantic_merge_schema import (
    HumanExceptionItem,
    SEVERE_CONFLICT_FLAGS,
    SemanticMergeJudgment,
)

# Default block flags for auto_confirm (all SEVERE + ambiguous_scope/broad/narrow)
DEFAULT_BLOCK_CONFIRM_FLAGS = frozenset(SEVERE_CONFLICT_FLAGS | {"ambiguous_scope", "too_broad", "too_narrow"})


@dataclass(frozen=True)
class SemanticMergeGateConfig:
    # Confirm gate
    auto_confirm_threshold: float = 0.82
    require_group_title: bool = True
    require_group_summary: bool = True
    require_evidence_alignment: bool = False  # True when configured via YAML
    require_workflow_judgment: bool = False   # True when configured via YAML
    block_confirm_flags: frozenset[str] = field(default_factory=lambda: DEFAULT_BLOCK_CONFIRM_FLAGS)

    # Reject gate
    auto_reject_threshold: float = 0.75
    require_reject_reason: bool = True
    require_reject_workflow: bool = False     # True when configured via YAML

    # Legacy / human_exception threshold
    human_review_threshold: float = 0.82

    # Legacy aliases kept for backwards compat
    require_reason_zh: bool = True


def config_from_dict(config: dict | None) -> SemanticMergeGateConfig:
    """Build gate config from the loaded YAML dict.

    Supports legacy flat structure and new nested `thresholds` block
    with per-gate options (Stage 2.9C).
    """
    raw = config or {}
    semantic = raw.get("semantic_merge", raw)
    thresholds = semantic.get("thresholds", {})

    def _threshold(value: object, fallback: float) -> float:
        if isinstance(value, dict):
            return float(value.get("confidence", fallback))
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                pass
        return fallback

    confirm_block = thresholds.get("auto_confirm", {})
    reject_block = thresholds.get("auto_reject", {})
    exception_block = thresholds.get("human_exception", {})

    auto_confirm = _threshold(confirm_block, float(semantic.get("auto_confirm_threshold", 0.82)))
    auto_reject = _threshold(reject_block, float(semantic.get("auto_reject_threshold", 0.75)))
    human_review = _threshold(exception_block, float(semantic.get("human_review_threshold", 0.82)))

    # Per-gate options
    require_title = bool(confirm_block.get("require_group_title", True)) if isinstance(confirm_block, dict) else True
    require_summary = bool(confirm_block.get("require_group_summary", True)) if isinstance(confirm_block, dict) else True
    require_ev = bool(confirm_block.get("require_evidence_alignment", False)) if isinstance(confirm_block, dict) else False
    require_wf = bool(confirm_block.get("require_workflow_judgment", False)) if isinstance(confirm_block, dict) else False

    raw_block_flags = confirm_block.get("block_conflict_flags", []) if isinstance(confirm_block, dict) else []
    block_flags = frozenset(str(f) for f in raw_block_flags) if raw_block_flags else DEFAULT_BLOCK_CONFIRM_FLAGS

    require_reject_reason = bool(reject_block.get("require_reason", True)) if isinstance(reject_block, dict) else True
    require_reject_wf = bool(reject_block.get("require_workflow_judgment", False)) if isinstance(reject_block, dict) else False

    return SemanticMergeGateConfig(
        auto_confirm_threshold=auto_confirm,
        require_group_title=require_title,
        require_group_summary=require_summary,
        require_evidence_alignment=require_ev,
        require_workflow_judgment=require_wf,
        block_confirm_flags=block_flags,
        auto_reject_threshold=auto_reject,
        require_reject_reason=require_reject_reason,
        require_reject_workflow=require_reject_wf,
        human_review_threshold=human_review,
        require_reason_zh=bool(semantic.get("require_reason_zh", True)),
    )


def determine_auto_action(
    decision: str,
    confidence: float,
    conflict_flags: list[str],
    suggested_group_title_zh: str | None,
    suggested_group_summary_zh: str | None,
    reason_zh: str,
    config: SemanticMergeGateConfig | None = None,
    evidence_alignment_zh: str | None = None,
    workflow_judgment_zh: str | None = None,
) -> str:
    gate_config = config or SemanticMergeGateConfig()
    flag_set = set(conflict_flags)

    if decision == "confirm_merge":
        # Block flags check (split from SEVERE_CONFLICT_FLAGS for confirm)
        blocked = flag_set & gate_config.block_confirm_flags
        reason_missing = gate_config.require_reason_zh and len((reason_zh or "").strip()) < 8
        title_missing = gate_config.require_group_title and not (suggested_group_title_zh or "").strip()
        summary_missing = gate_config.require_group_summary and not (suggested_group_summary_zh or "").strip()
        ev_missing = gate_config.require_evidence_alignment and not (evidence_alignment_zh or "").strip()
        wf_missing = gate_config.require_workflow_judgment and not (workflow_judgment_zh or "").strip()

        if (
            confidence >= gate_config.auto_confirm_threshold
            and not blocked
            and not reason_missing
            and not title_missing
            and not summary_missing
            and not ev_missing
            and not wf_missing
        ):
            return "auto_confirm"
        return "human_exception"

    if decision == "reject_merge":
        reason_missing = gate_config.require_reject_reason and len((reason_zh or "").strip()) < 8
        wf_missing = gate_config.require_reject_workflow and not (workflow_judgment_zh or "").strip()
        if (
            confidence >= gate_config.auto_reject_threshold
            and not reason_missing
            and not wf_missing
        ):
            return "auto_reject"
        return "human_exception"

    # maybe_merge and unknown
    return "human_exception"


def should_enter_exception_queue(
    judgment: SemanticMergeJudgment,
    config: SemanticMergeGateConfig | None = None,
) -> bool:
    if judgment.auto_action in ("auto_confirm", "auto_reject"):
        return False
    if judgment.auto_action == "human_exception":
        return True
    gate_config = config or SemanticMergeGateConfig()
    if judgment.decision == "maybe_merge":
        return True
    if judgment.confidence < gate_config.human_review_threshold:
        return True
    if set(judgment.conflict_flags) & SEVERE_CONFLICT_FLAGS:
        return True
    if len(judgment.reason_zh.strip()) < 8:
        return True
    if judgment.decision == "confirm_merge" and (
        not (judgment.suggested_group_title_zh or "").strip()
        or not (judgment.suggested_group_summary_zh or "").strip()
    ):
        return True
    return False


def build_exception_item(
    judgment: SemanticMergeJudgment,
    exception_id: str,
    config: SemanticMergeGateConfig | None = None,
) -> HumanExceptionItem:
    reason = exception_reason(judgment, config)
    return HumanExceptionItem(
        exception_id=exception_id,
        judgment_id=judgment.judgment_id,
        merge_candidate_id=judgment.merge_candidate_id,
        cluster_id_a=judgment.cluster_id_a,
        cluster_id_b=judgment.cluster_id_b,
        exception_reason=reason,
        priority=exception_priority(judgment, reason),
        decision=judgment.decision,
        confidence=judgment.confidence,
        conflict_flags=judgment.conflict_flags,
        reason_zh=judgment.reason_zh,
    )


def exception_reason(
    judgment: SemanticMergeJudgment,
    config: SemanticMergeGateConfig | None = None,
) -> str:
    gate_config = config or SemanticMergeGateConfig()
    flag_set = set(judgment.conflict_flags)
    if judgment.decision == "maybe_merge":
        return "AI 判断为暂不确定，需要人工裁决。"
    if judgment.decision == "confirm_merge":
        if flag_set & gate_config.block_confirm_flags:
            return "AI 建议合并但包含阻断标记，需要人工核查。"
        if judgment.confidence < gate_config.auto_confirm_threshold:
            return "AI 判断置信度低于自动确认阈值。"
        if not (judgment.suggested_group_title_zh or "").strip():
            return "AI 建议合并但缺少合并后标题。"
        if not (judgment.suggested_group_summary_zh or "").strip():
            return "AI 建议合并但缺少合并后摘要。"
        return "AI 判断未满足自动确认条件。"
    if judgment.decision == "reject_merge":
        if judgment.confidence < gate_config.auto_reject_threshold:
            return "AI 建议拒绝但置信度低于自动拒绝阈值。"
        if len(judgment.reason_zh.strip()) < 8:
            return "AI 判断理由过短，需要人工补充判断。"
        return "AI 建议拒绝但缺少工作流判断说明。"
    if judgment.confidence < gate_config.human_review_threshold:
        return "AI 判断置信度低于自动处理阈值。"
    if flag_set & SEVERE_CONFLICT_FLAGS:
        return "AI 判断包含严重冲突标记，需要人工核查。"
    if len(judgment.reason_zh.strip()) < 8:
        return "AI 判断理由过短或不足，需要人工补充判断。"
    return "AI 判断未满足自动处理条件。"


def exception_priority(judgment: SemanticMergeJudgment, reason: str | None = None) -> str:
    severe_flags = set(judgment.conflict_flags) & SEVERE_CONFLICT_FLAGS
    if severe_flags or "严重冲突" in (reason or ""):
        return "high"
    if judgment.confidence < 0.7 or judgment.decision == "maybe_merge":
        return "medium"
    return "low"
