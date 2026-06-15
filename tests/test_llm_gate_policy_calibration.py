"""Tests for gate policy calibration (Stage 2.9C)."""
from __future__ import annotations

import pytest

from demand_radar.semantic_merge.exception_queue import (
    SemanticMergeGateConfig,
    config_from_dict,
    determine_auto_action,
)


def test_auto_reject_threshold_0_75():
    """reject_merge with confidence 0.78 should auto_reject with 0.75 threshold."""
    cfg = SemanticMergeGateConfig(auto_reject_threshold=0.75)
    action = determine_auto_action(
        decision="reject_merge",
        confidence=0.78,
        conflict_flags=[],
        suggested_group_title_zh=None,
        suggested_group_summary_zh=None,
        reason_zh="用户工作流完全不同。",
        config=cfg,
        workflow_judgment_zh="两个cluster工作流完全不同。",
    )
    assert action == "auto_reject"


def test_auto_reject_below_threshold():
    """reject_merge with confidence 0.70 should go to exception with 0.75 threshold."""
    cfg = SemanticMergeGateConfig(auto_reject_threshold=0.75)
    action = determine_auto_action(
        decision="reject_merge",
        confidence=0.70,
        conflict_flags=[],
        suggested_group_title_zh=None,
        suggested_group_summary_zh=None,
        reason_zh="用户工作流完全不同。",
        config=cfg,
        workflow_judgment_zh="两个cluster工作流完全不同。",
    )
    assert action == "human_exception"


def test_auto_confirm_threshold_0_82():
    """confirm_merge with confidence 0.83 should auto_confirm with 0.82 threshold."""
    cfg = SemanticMergeGateConfig(auto_confirm_threshold=0.82)
    action = determine_auto_action(
        decision="confirm_merge",
        confidence=0.83,
        conflict_flags=[],
        suggested_group_title_zh="需求组标题",
        suggested_group_summary_zh="需求组摘要说明",
        reason_zh="两个cluster属于同一工作流。",
        config=cfg,
        evidence_alignment_zh="证据对齐说明",
        workflow_judgment_zh="工作流判断说明",
    )
    assert action == "auto_confirm"


def test_auto_confirm_with_block_flag():
    """confirm_merge blocked by block_conflict_flags."""
    cfg = SemanticMergeGateConfig(
        auto_confirm_threshold=0.82,
        block_confirm_flags=frozenset({"different_persona", "different_workflow"}),
    )
    action = determine_auto_action(
        decision="confirm_merge",
        confidence=0.90,
        conflict_flags=["different_persona"],
        suggested_group_title_zh="需求组标题",
        suggested_group_summary_zh="需求组摘要说明",
        reason_zh="两个cluster属于同一工作流。",
        config=cfg,
        evidence_alignment_zh="证据对齐",
        workflow_judgment_zh="工作流判断",
    )
    assert action == "human_exception"


def test_confirm_missing_title_goes_to_exception():
    cfg = SemanticMergeGateConfig(auto_confirm_threshold=0.82, require_group_title=True)
    action = determine_auto_action(
        decision="confirm_merge",
        confidence=0.90,
        conflict_flags=[],
        suggested_group_title_zh="",
        suggested_group_summary_zh="有摘要",
        reason_zh="两个cluster属于同一工作流。",
        config=cfg,
        evidence_alignment_zh="有证据",
        workflow_judgment_zh="有工作流",
    )
    assert action == "human_exception"


def test_confirm_missing_summary_goes_to_exception():
    cfg = SemanticMergeGateConfig(auto_confirm_threshold=0.82, require_group_summary=True)
    action = determine_auto_action(
        decision="confirm_merge",
        confidence=0.90,
        conflict_flags=[],
        suggested_group_title_zh="有标题",
        suggested_group_summary_zh=None,
        reason_zh="两个cluster属于同一工作流。",
        config=cfg,
        evidence_alignment_zh="有证据",
        workflow_judgment_zh="有工作流",
    )
    assert action == "human_exception"


def test_reject_missing_workflow_goes_to_exception():
    cfg = SemanticMergeGateConfig(auto_reject_threshold=0.75, require_reject_workflow=True)
    action = determine_auto_action(
        decision="reject_merge",
        confidence=0.82,
        conflict_flags=[],
        suggested_group_title_zh=None,
        suggested_group_summary_zh=None,
        reason_zh="用户工作流完全不同。",
        config=cfg,
        workflow_judgment_zh="",
    )
    assert action == "human_exception"


def test_maybe_always_exception():
    cfg = SemanticMergeGateConfig()
    action = determine_auto_action(
        decision="maybe_merge",
        confidence=0.99,
        conflict_flags=[],
        suggested_group_title_zh=None,
        suggested_group_summary_zh=None,
        reason_zh="不确定",
        config=cfg,
    )
    assert action == "human_exception"


def test_config_from_dict_calibrated():
    """config_from_dict should read calibrated thresholds correctly."""
    raw = {
        "semantic_merge": {
            "thresholds": {
                "auto_confirm": {"confidence": 0.82, "require_group_title": True, "require_group_summary": True,
                                  "block_conflict_flags": ["different_persona", "different_workflow"]},
                "auto_reject": {"confidence": 0.75, "require_reason": True, "require_workflow_judgment": True},
                "human_exception": {"confidence": 0.82},
            }
        }
    }
    cfg = config_from_dict(raw)
    assert cfg.auto_confirm_threshold == 0.82
    assert cfg.auto_reject_threshold == 0.75
    assert "different_persona" in cfg.block_confirm_flags
    assert "different_workflow" in cfg.block_confirm_flags
    assert cfg.require_reject_workflow is True