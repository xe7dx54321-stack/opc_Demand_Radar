"""Tests for Stage 2.9 LLM output parser."""
from __future__ import annotations

import json
import pytest

from demand_radar.semantic_merge.llm_output_parser import LLMParseError, parse_llm_output


def _valid_json(**overrides) -> str:
    data = {
        "decision": "confirm_merge",
        "confidence": 0.90,
        "reason_zh": "两个主题核心痛点高度一致，建议合并。",
        "evidence_alignment_zh": "证据对齐说明",
        "workflow_judgment_zh": "工作流判断说明",
        "suggested_group_title_zh": "用户在工作流中遇到的信息分散问题",
        "suggested_group_summary_zh": "两个需求均涉及信息分散导致的人工整理负担。",
        "conflict_flags": [],
    }
    data.update(overrides)
    return json.dumps(data, ensure_ascii=False)


def test_pure_json_parsed():
    result = parse_llm_output(_valid_json())
    assert result["decision"] == "confirm_merge"
    assert result["confidence"] == 0.90


def test_markdown_code_block_stripped():
    raw = "```json\n" + _valid_json() + "\n```"
    result = parse_llm_output(raw)
    assert result["decision"] == "confirm_merge"


def test_json_with_surrounding_text():
    raw = "Here is my analysis:\n" + _valid_json() + "\n\nThat is all."
    result = parse_llm_output(raw)
    assert result["decision"] == "confirm_merge"


def test_invalid_json_raises():
    with pytest.raises(LLMParseError):
        parse_llm_output("this is not json at all")


def test_invalid_decision_raises():
    with pytest.raises(LLMParseError, match="Invalid decision"):
        parse_llm_output(_valid_json(decision="bad_value"))


def test_confidence_out_of_range_raises():
    with pytest.raises(LLMParseError, match="out of range"):
        parse_llm_output(_valid_json(confidence=1.5))


def test_confidence_not_a_number_raises():
    with pytest.raises(LLMParseError, match="not a number"):
        parse_llm_output(_valid_json(confidence="high"))


def test_empty_reason_zh_raises():
    with pytest.raises(LLMParseError, match="empty"):
        parse_llm_output(_valid_json(reason_zh=""))


def test_reason_zh_no_chinese_raises():
    with pytest.raises(LLMParseError, match="Chinese"):
        parse_llm_output(_valid_json(reason_zh="No Chinese at all"))


def test_confirm_merge_missing_title_raises():
    with pytest.raises(LLMParseError, match="suggested_group_title_zh"):
        parse_llm_output(_valid_json(suggested_group_title_zh=""))


def test_confirm_merge_missing_summary_raises():
    with pytest.raises(LLMParseError, match="suggested_group_summary_zh"):
        parse_llm_output(_valid_json(suggested_group_summary_zh=""))


def test_reject_merge_no_title_required():
    raw = json.dumps({
        "decision": "reject_merge",
        "confidence": 0.88,
        "reason_zh": "工作流完全不同，不应合并。",
        "evidence_alignment_zh": "证据偏弱",
        "workflow_judgment_zh": "工作流不同",
        "conflict_flags": ["different_workflow"],
    })
    result = parse_llm_output(raw)
    assert result["decision"] == "reject_merge"


def test_invalid_conflict_flag_raises():
    with pytest.raises(LLMParseError, match="conflict_flag"):
        parse_llm_output(_valid_json(conflict_flags=["not_a_valid_flag"]))


def test_conflict_flags_must_be_list_raises():
    with pytest.raises(LLMParseError, match="list"):
        parse_llm_output(_valid_json(conflict_flags="different_workflow"))


def test_maybe_merge_no_title_required():
    raw = json.dumps({
        "decision": "maybe_merge",
        "confidence": 0.60,
        "reason_zh": "证据不足以自动判断，需要人工裁决。",
        "conflict_flags": [],
    })
    result = parse_llm_output(raw)
    assert result["decision"] == "maybe_merge"
