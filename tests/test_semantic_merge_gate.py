"""Tests for semantic merge gate logic."""
from __future__ import annotations

import pytest

from demand_radar.semantic_merge.exception_queue import (
    SemanticMergeGateConfig,
    config_from_dict,
    determine_auto_action,
    exception_priority,
    exception_reason,
    should_enter_exception_queue,
)
from demand_radar.semantic_merge.semantic_merge_schema import SemanticMergeJudgment


def _make_judgment(**kwargs) -> SemanticMergeJudgment:
    defaults = dict(
        judgment_id="j001",
        merge_candidate_id="mc001",
        cluster_id_a="ca001",
        cluster_id_b="cb001",
        decision="confirm_merge",
        confidence=0.90,
        reason_zh="两个主题核心痛点高度一致。",
        auto_action="auto_confirm",
        judge_mode="rule_based_stub",
        suggested_group_title_zh="测试合并后标题",
        suggested_group_summary_zh="测试合并后摘要内容",
    )
    defaults.update(kwargs)
    return SemanticMergeJudgment(**defaults)


# ------------------------------------------------------------------
# config_from_dict: supports both legacy flat and new thresholds block
# ------------------------------------------------------------------

def test_config_from_dict_legacy_flat():
    cfg = config_from_dict({"semantic_merge": {"auto_confirm_threshold": 0.80}})
    assert cfg.auto_confirm_threshold == 0.80


def test_config_from_dict_new_thresholds_block():
    cfg = config_from_dict({"semantic_merge": {"thresholds": {"auto_confirm": 0.75, "auto_reject": 0.80, "human_exception": 0.70}}})
    assert cfg.auto_confirm_threshold == 0.75
    assert cfg.auto_reject_threshold == 0.80
    assert cfg.human_review_threshold == 0.70


def test_config_from_dict_defaults():
    cfg = config_from_dict({})
    assert cfg.auto_confirm_threshold == 0.82
    assert cfg.auto_reject_threshold == 0.75
    assert cfg.human_review_threshold == 0.82


# ------------------------------------------------------------------
# determine_auto_action
# ------------------------------------------------------------------

def test_auto_confirm_high_confidence_no_flags():
    action = determine_auto_action(
        decision="confirm_merge",
        confidence=0.90,
        conflict_flags=[],
        suggested_group_title_zh="有效标题",
        suggested_group_summary_zh="有效摘要内容",
        reason_zh="两个主题核心痛点高度一致。",
    )
    assert action == "auto_confirm"


def test_auto_confirm_blocked_by_low_confidence():
    action = determine_auto_action(
        decision="confirm_merge",
        confidence=0.70,
        conflict_flags=[],
        suggested_group_title_zh="有效标题",
        suggested_group_summary_zh="有效摘要内容",
        reason_zh="两个主题核心痛点高度一致。",
    )
    assert action == "human_exception"


def test_auto_confirm_blocked_by_severe_flag():
    action = determine_auto_action(
        decision="confirm_merge",
        confidence=0.90,
        conflict_flags=["different_persona"],
        suggested_group_title_zh="有效标题",
        suggested_group_summary_zh="有效摘要内容",
        reason_zh="两个主题核心痛点高度一致。",
    )
    assert action == "human_exception"


def test_auto_reject_high_confidence():
    action = determine_auto_action(
        decision="reject_merge",
        confidence=0.88,
        conflict_flags=[],
        suggested_group_title_zh=None,
        suggested_group_summary_zh=None,
        reason_zh="工作流完全不同，不应合并。",
    )
    assert action == "auto_reject"


def test_auto_reject_low_confidence_becomes_exception():
    action = determine_auto_action(
        decision="reject_merge",
        confidence=0.60,
        conflict_flags=[],
        suggested_group_title_zh=None,
        suggested_group_summary_zh=None,
        reason_zh="工作流完全不同，不应合并。",
    )
    assert action == "human_exception"


def test_maybe_merge_always_exception():
    action = determine_auto_action(
        decision="maybe_merge",
        confidence=0.99,
        conflict_flags=[],
        suggested_group_title_zh=None,
        suggested_group_summary_zh=None,
        reason_zh="证据不足以自动判断。",
    )
    assert action == "human_exception"


def test_confirm_missing_title_becomes_exception():
    action = determine_auto_action(
        decision="confirm_merge",
        confidence=0.90,
        conflict_flags=[],
        suggested_group_title_zh="",
        suggested_group_summary_zh="有效摘要内容",
        reason_zh="两个主题核心痛点高度一致。",
    )
    assert action == "human_exception"


# ------------------------------------------------------------------
# should_enter_exception_queue
# ------------------------------------------------------------------

def test_auto_confirm_does_not_enter_queue():
    judgment = _make_judgment(auto_action="auto_confirm", confidence=0.90)
    assert not should_enter_exception_queue(judgment)


def test_auto_reject_does_not_enter_queue():
    judgment = _make_judgment(
        decision="reject_merge",
        auto_action="auto_reject",
        confidence=0.88,
        conflict_flags=[],
    )
    assert not should_enter_exception_queue(judgment)


def test_maybe_merge_enters_queue():
    judgment = _make_judgment(
        decision="maybe_merge",
        auto_action="human_exception",
        confidence=0.70,
    )
    assert should_enter_exception_queue(judgment)


def test_severe_conflict_flags_block_auto_confirm():
    """If a judgment has severe conflict_flags, determine_auto_action returns human_exception.
    So auto_confirm + severe_flags cannot coexist; this test verifies the gate blocks it
    at action-determination time rather than at should_enter_exception_queue time.
    """
    # A confirm judgment with severe flags would be classified as human_exception by determine_auto_action.
    # should_enter_exception_queue correctly returns True for human_exception.
    action = determine_auto_action(
        decision="confirm_merge",
        confidence=0.90,
        conflict_flags=["different_persona"],
        suggested_group_title_zh="有效标题",
        suggested_group_summary_zh="有效摘要内容",
        reason_zh="两个主题核心痛点高度一致。",
    )
    assert action == "human_exception"


# ------------------------------------------------------------------
# exception_priority
# ------------------------------------------------------------------

def test_severe_flags_give_high_priority():
    judgment = _make_judgment(conflict_flags=["different_workflow"])
    assert exception_priority(judgment) == "high"


def test_maybe_merge_gives_medium_priority():
    judgment = _make_judgment(decision="maybe_merge", auto_action="human_exception", confidence=0.55)
    assert exception_priority(judgment) == "medium"


def test_auto_confirm_low_priority():
    judgment = _make_judgment(auto_action="auto_confirm", confidence=0.90)
    assert exception_priority(judgment) == "low"


