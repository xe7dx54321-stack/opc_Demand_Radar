"""Robust parser for raw LLM text output in Stage 2.9 semantic merge.

Handles:
  - Pure JSON strings
  - JSON wrapped in ```json ... ``` markdown fences
  - JSON preceded / followed by explanatory text
  - Truncated JSON (output cut mid-string) -- Stage 2.9E repair
  - Partial field extraction from truncated output
  - Invalid JSON -> raises LLMParseError so caller routes to human_exception
"""
from __future__ import annotations

import json
import re
from typing import Any

from demand_radar.semantic_merge.semantic_merge_schema import (
    VALID_CONFLICT_FLAGS,
    VALID_SEMANTIC_MERGE_DECISIONS,
)


class LLMParseError(ValueError):
    """Raised when the raw LLM text cannot be parsed into a valid judgment dict."""


def parse_llm_output(raw: str) -> dict[str, Any]:
    """Parse raw LLM text into a validated dict suitable for SemanticMergeJudgment.

    Raises ``LLMParseError`` on any parse or validation failure.
    """
    text = (raw or "").strip()
    data = _extract_json(text)
    _validate(data)
    return data


def is_truncated_output(raw: str) -> bool:
    """Return True if the output looks like a truncated JSON (opens but doesn't close)."""
    text = (raw or "").strip()
    # Remove any markdown fences
    for fence in ("```json", "```JSON", "```"):
        if text.startswith(fence):
            text = text[len(fence):]
            break
    text = text.strip()
    if not text.startswith("{"):
        return False
    # Count open vs close braces (rough check)
    opens = text.count("{")
    closes = text.count("}")
    return opens > closes


def _extract_json(text: str) -> dict[str, Any]:
    """Try multiple extraction strategies in order of strictness."""
    # 1. Direct JSON parse
    try:
        return _as_object(json.loads(text))
    except (json.JSONDecodeError, TypeError, LLMParseError):
        pass

    # 2. Strip markdown fences
    for fence in ("```json", "```JSON", "```"):
        if text.startswith(fence):
            stripped = text[len(fence):]
            if stripped.endswith("```"):
                stripped = stripped[:-3]
            try:
                return _as_object(json.loads(stripped.strip()))
            except (json.JSONDecodeError, TypeError, LLMParseError):
                pass

    # 3. Extract first {...} block (tolerates surrounding prose)
    match = re.search(r"\{.*?\}", text, re.DOTALL)
    if match:
        try:
            return _as_object(json.loads(match.group()))
        except (json.JSONDecodeError, TypeError, LLMParseError):
            pass

    # 4. Greedy {...} block -- catches larger objects
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return _as_object(json.loads(match.group()))
        except (json.JSONDecodeError, TypeError, LLMParseError):
            pass

    # 5. Truncated JSON repair -- Stage 2.9E
    repaired = _repair_truncated_json(text)
    if repaired is not None:
        try:
            return _as_object(repaired)
        except LLMParseError:
            pass

    raise LLMParseError(f"Cannot extract JSON from LLM output: {text[:200]!r}")


def _repair_truncated_json(text: str) -> dict[str, Any] | None:
    """Attempt to recover fields from a truncated JSON string.

    Strategy:
    1. Find the opening ``{``.
    2. Extract key-value pairs that are fully present using regex.
    3. Try to reconstruct a valid partial object.
    4. Return None if not enough fields are recoverable.
    """
    # Locate the JSON start
    start = text.find("{")
    if start < 0:
        return None
    fragment = text[start:]

    extracted: dict[str, Any] = {}

    # Extract string values: "key": "value" (handles escaped quotes inside value)
    str_pat = re.compile(r'"([^"]+)"\s*:\s*"((?:[^"\\]|\\.)*)"')
    for m in str_pat.finditer(fragment):
        key, value = m.group(1), m.group(2)
        # Unescape
        try:
            value = json.loads(f'"{value}"')
        except json.JSONDecodeError:
            pass
        extracted[key] = value

    # Extract numeric values: "key": 0.85
    num_pat = re.compile(r'"([^"]+)"\s*:\s*([0-9]+(?:\.[0-9]+)?)')
    for m in num_pat.finditer(fragment):
        key = m.group(1)
        if key not in extracted:
            try:
                extracted[key] = float(m.group(2))
            except ValueError:
                pass

    # Extract array values: "conflict_flags": [...]  -- only if complete
    arr_pat = re.compile(r'"([^"]+)"\s*:\s*(\[[^\]]*\])')
    for m in arr_pat.finditer(fragment):
        key = m.group(1)
        if key not in extracted:
            try:
                extracted[key] = json.loads(m.group(2))
            except json.JSONDecodeError:
                pass

    # Must have at least decision and confidence to be usable
    if "decision" not in extracted or "confidence" not in extracted:
        return None

    # Fill in required fields with safe defaults if missing
    extracted.setdefault("reason_zh", "")
    extracted.setdefault("evidence_alignment_zh", "")
    extracted.setdefault("workflow_judgment_zh", "")
    extracted.setdefault("suggested_group_title_zh", "")
    extracted.setdefault("suggested_group_summary_zh", "")
    extracted.setdefault("conflict_flags", [])

    return extracted


def _as_object(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise LLMParseError(f"Expected JSON object, got {type(value).__name__}")
    return value


def _validate(data: dict[str, Any]) -> None:
    """Raise LLMParseError if required fields are missing or invalid."""
    decision = str(data.get("decision", "")).strip()
    if decision not in VALID_SEMANTIC_MERGE_DECISIONS:
        raise LLMParseError(f"Invalid decision: {decision!r}")

    raw_confidence = data.get("confidence")
    try:
        confidence = float(raw_confidence)
    except (TypeError, ValueError):
        raise LLMParseError(f"confidence is not a number: {raw_confidence!r}")
    if not (0.0 <= confidence <= 1.0):
        raise LLMParseError(f"confidence out of range: {confidence}")

    reason_zh = str(data.get("reason_zh", "")).strip()
    if not reason_zh:
        raise LLMParseError("reason_zh is empty")

    # reason_zh must contain at least some Chinese characters
    # (truncated outputs with empty reason_zh are handled by _repair_truncated_json
    #  which sets reason_zh to "" -- callers should treat these as partial)
    has_cjk = any("\u4e00" <= ch <= "\u9fff" for ch in reason_zh)
    if not has_cjk:
        raise LLMParseError("reason_zh contains no Chinese characters")

    if decision == "confirm_merge":
        title = str(data.get("suggested_group_title_zh", "")).strip()
        summary = str(data.get("suggested_group_summary_zh", "")).strip()
        if not title:
            raise LLMParseError("confirm_merge requires suggested_group_title_zh")
        if not summary:
            raise LLMParseError("confirm_merge requires suggested_group_summary_zh")

    raw_flags = data.get("conflict_flags", [])
    if not isinstance(raw_flags, list):
        raise LLMParseError(f"conflict_flags must be a list, got {type(raw_flags).__name__}")
    for flag in raw_flags:
        if str(flag).strip() not in VALID_CONFLICT_FLAGS:
            raise LLMParseError(f"Invalid conflict_flag: {flag!r}")
