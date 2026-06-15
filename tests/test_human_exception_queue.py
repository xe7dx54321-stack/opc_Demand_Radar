"""Tests for human exception queue in Stage 2.8."""
from __future__ import annotations

from pathlib import Path

from demand_radar.semantic_merge.exception_queue import build_exception_item, exception_priority, exception_reason
from demand_radar.semantic_merge.semantic_merge_schema import HumanExceptionItem, SemanticMergeJudgment
from demand_radar.semantic_merge.semantic_merge_store import (
    build_human_exception_queue,
    load_human_exception_items,
    write_human_exception_items,
)


def _make_exception_judgment(judgment_id: str, decision: str = "maybe_merge", confidence: float = 0.55) -> SemanticMergeJudgment:
    return SemanticMergeJudgment(
        judgment_id=judgment_id,
        merge_candidate_id=f"mc_{judgment_id}",
        cluster_id_a=f"ca_{judgment_id}",
        cluster_id_b=f"cb_{judgment_id}",
        decision=decision,
        confidence=confidence,
        reason_zh="证据不足以自动判断，需要人工裁决。",
        auto_action="human_exception",
        judge_mode="rule_based_stub",
    )


def test_build_human_exception_queue_assigns_ids():
    j1 = _make_exception_judgment("j001")
    j2 = _make_exception_judgment("j002")
    items = build_human_exception_queue([j1, j2])
    assert len(items) == 2
    assert items[0].exception_id != items[1].exception_id
    assert items[0].judgment_id == "j001"
    assert items[1].judgment_id == "j002"


def test_build_human_exception_queue_priority_assigned():
    j = _make_exception_judgment("j001")
    items = build_human_exception_queue([j])
    assert items[0].priority in ("high", "medium", "low")


def test_build_exception_item_with_severe_flag():
    j = SemanticMergeJudgment(
        judgment_id="j001",
        merge_candidate_id="mc001",
        cluster_id_a="ca001",
        cluster_id_b="cb001",
        decision="maybe_merge",
        confidence=0.50,
        reason_zh="工作流和用户角色不同，难以自动合并。",
        auto_action="human_exception",
        judge_mode="rule_based_stub",
        conflict_flags=["different_persona"],
    )
    item = build_exception_item(j, "ex001")
    assert item.priority == "high"


def test_write_and_load_exception_queue_roundtrip(tmp_path: Path):
    path = tmp_path / "exceptions.jsonl"
    j = _make_exception_judgment("j001")
    items = build_human_exception_queue([j])
    write_human_exception_items(items, path)
    loaded = load_human_exception_items(path)
    assert len(loaded) == 1
    assert loaded[0].judgment_id == "j001"


def test_exception_reason_maybe_merge():
    j = _make_exception_judgment("j001", decision="maybe_merge")
    reason = exception_reason(j)
    assert "暂不确定" in reason or "maybe" in reason or "裁决" in reason


def test_exception_reason_low_confidence():
    j = SemanticMergeJudgment(
        judgment_id="j001",
        merge_candidate_id="mc001",
        cluster_id_a="ca001",
        cluster_id_b="cb001",
        decision="reject_merge",
        confidence=0.50,
        reason_zh="工作流不同，不应合并。",
        auto_action="human_exception",
        judge_mode="rule_based_stub",
    )
    reason = exception_reason(j)
    assert "置信度" in reason or "阈值" in reason or "confidence" in reason.lower()
