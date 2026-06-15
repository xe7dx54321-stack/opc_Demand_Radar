"""Tests for Stage 2.8 semantic merge schema."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from demand_radar.semantic_merge.semantic_merge_schema import (
    AIReviewedClusterGroup,
    HumanExceptionItem,
    SemanticMergeHumanAudit,
    SemanticMergeJudgment,
    SEVERE_CONFLICT_FLAGS,
    VALID_CONFLICT_FLAGS,
)
from demand_radar.state.raw_store import utc_now_iso


def _make_judgment(**kwargs) -> SemanticMergeJudgment:
    defaults = dict(
        judgment_id="j001",
        merge_candidate_id="mc001",
        cluster_id_a="ca001",
        cluster_id_b="cb001",
        decision="confirm_merge",
        confidence=0.90,
        reason_zh="两个主题核心痛点高度一致，建议合并。",
        auto_action="auto_confirm",
        judge_mode="rule_based_stub",
    )
    defaults.update(kwargs)
    return SemanticMergeJudgment(**defaults)


def test_valid_auto_confirm_judgment():
    j = _make_judgment(
        suggested_group_title_zh="用户在工作流中遇到的信息分散问题",
        suggested_group_summary_zh="两个需求均涉及信息分散导致的人工整理负担。",
    )
    assert j.auto_action == "auto_confirm"
    assert j.confidence == 0.90


def test_auto_confirm_requires_confirm_merge_decision():
    with pytest.raises(ValidationError):
        _make_judgment(decision="reject_merge", auto_action="auto_confirm")


def test_auto_reject_requires_reject_merge_decision():
    with pytest.raises(ValidationError):
        _make_judgment(decision="confirm_merge", auto_action="auto_reject")


def test_confidence_out_of_range_rejected():
    with pytest.raises(ValidationError):
        _make_judgment(confidence=1.5)


def test_reason_must_contain_chinese():
    with pytest.raises(ValidationError):
        _make_judgment(reason_zh="No Chinese here at all.")


def test_invalid_conflict_flag_rejected():
    with pytest.raises(ValidationError):
        _make_judgment(conflict_flags=["not_a_real_flag"])


def test_cluster_ids_must_differ():
    with pytest.raises(ValidationError):
        _make_judgment(cluster_id_a="same", cluster_id_b="same")


def test_valid_auto_reject_judgment():
    j = _make_judgment(
        decision="reject_merge",
        auto_action="auto_reject",
        confidence=0.87,
        conflict_flags=["different_persona", "different_workflow"],
    )
    assert j.decision == "reject_merge"
    assert "different_persona" in j.conflict_flags


def test_valid_maybe_merge_judgment():
    j = _make_judgment(
        decision="maybe_merge",
        auto_action="human_exception",
        confidence=0.65,
    )
    assert j.auto_action == "human_exception"


def test_severe_conflict_flags_subset_of_valid():
    assert SEVERE_CONFLICT_FLAGS <= VALID_CONFLICT_FLAGS


def test_ai_reviewed_cluster_group_requires_two_clusters():
    with pytest.raises(ValidationError):
        AIReviewedClusterGroup(
            group_id="g001",
            group_title_zh="测试组",
            group_summary_zh="测试摘要内容",
            cluster_ids=["only_one"],
            related_pain_point_ids=["p001", "p002"],
            evidence_count=2,
            source_count=1,
            created_from_judgment_ids=["j001"],
        )


def test_ai_reviewed_cluster_group_title_must_be_chinese():
    with pytest.raises(ValidationError):
        AIReviewedClusterGroup(
            group_id="g001",
            group_title_zh="No Chinese",
            group_summary_zh="摘要内容",
            cluster_ids=["c001", "c002"],
            related_pain_point_ids=["p001", "p002"],
            evidence_count=2,
            source_count=1,
            created_from_judgment_ids=["j001"],
        )


def test_human_exception_item_valid():
    item = HumanExceptionItem(
        exception_id="ex001",
        judgment_id="j001",
        merge_candidate_id="mc001",
        cluster_id_a="ca001",
        cluster_id_b="cb001",
        exception_reason="AI 判断为暂不确定，需要人工裁决。",
        priority="high",
        decision="maybe_merge",
        confidence=0.50,
        reason_zh="需要进一步判断。",
    )
    assert item.priority == "high"


def test_semantic_merge_human_audit_valid():
    audit = SemanticMergeHumanAudit(
        audit_id="audit001",
        judgment_id="j001",
        merge_candidate_id="mc001",
        label="correct_to_confirm",
    )
    assert audit.label == "correct_to_confirm"


def test_semantic_merge_human_audit_invalid_label():
    with pytest.raises(ValidationError):
        SemanticMergeHumanAudit(
            audit_id="audit001",
            judgment_id="j001",
            merge_candidate_id="mc001",
            label="not_a_valid_label",
        )
