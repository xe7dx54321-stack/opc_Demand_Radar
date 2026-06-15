"""Tests for truth_input_loader.py"""
import json
import pytest
from pathlib import Path
from demand_radar.truth_scoring.truth_input_loader import (
    load_reviewed_groups,
    resolve_source_type_label,
)


def _write_jsonl(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")


def test_load_calibrated_llm(tmp_path, monkeypatch):
    import demand_radar.truth_scoring.truth_input_loader as loader
    monkeypatch.setattr(loader, "CALIBRATED_LLM_PATH", tmp_path / "calibrated.jsonl")
    monkeypatch.setattr(loader, "LLM_PATH", tmp_path / "llm.jsonl")
    monkeypatch.setattr(loader, "AI_PATH", tmp_path / "ai.jsonl")
    monkeypatch.setattr(loader, "HUMAN_PATH", tmp_path / "human.jsonl")
    monkeypatch.setattr(loader, "SOURCE_PATHS", {
        "calibrated_llm": tmp_path / "calibrated.jsonl",
        "llm": tmp_path / "llm.jsonl",
        "ai": tmp_path / "ai.jsonl",
        "human": tmp_path / "human.jsonl",
    })
    _write_jsonl(tmp_path / "calibrated.jsonl", [{"group_id": "g1", "group_title_zh": "测试"}])
    groups = load_reviewed_groups("calibrated_llm")
    assert len(groups) == 1
    assert groups[0]["_source_type"] == "calibrated_llm"


def test_auto_fallback(tmp_path, monkeypatch):
    import demand_radar.truth_scoring.truth_input_loader as loader
    monkeypatch.setattr(loader, "CALIBRATED_LLM_PATH", tmp_path / "calibrated.jsonl")
    monkeypatch.setattr(loader, "LLM_PATH", tmp_path / "llm.jsonl")
    monkeypatch.setattr(loader, "AI_PATH", tmp_path / "ai.jsonl")
    monkeypatch.setattr(loader, "HUMAN_PATH", tmp_path / "human.jsonl")
    monkeypatch.setattr(loader, "SOURCE_PATHS", {
        "calibrated_llm": tmp_path / "calibrated.jsonl",
        "llm": tmp_path / "llm.jsonl",
        "ai": tmp_path / "ai.jsonl",
        "human": tmp_path / "human.jsonl",
    })
    # Only ai.jsonl exists
    _write_jsonl(tmp_path / "ai.jsonl", [{"group_id": "g2", "group_title_zh": "回调"}])
    groups = load_reviewed_groups("auto")
    assert len(groups) == 1
    assert groups[0]["_source_type"] == "ai"


def test_combined_no_duplicates(tmp_path, monkeypatch):
    import demand_radar.truth_scoring.truth_input_loader as loader
    monkeypatch.setattr(loader, "CALIBRATED_LLM_PATH", tmp_path / "calibrated.jsonl")
    monkeypatch.setattr(loader, "LLM_PATH", tmp_path / "llm.jsonl")
    monkeypatch.setattr(loader, "AI_PATH", tmp_path / "ai.jsonl")
    monkeypatch.setattr(loader, "HUMAN_PATH", tmp_path / "human.jsonl")
    monkeypatch.setattr(loader, "SOURCE_PATHS", {
        "calibrated_llm": tmp_path / "calibrated.jsonl",
        "llm": tmp_path / "llm.jsonl",
        "ai": tmp_path / "ai.jsonl",
        "human": tmp_path / "human.jsonl",
    })
    _write_jsonl(tmp_path / "calibrated.jsonl", [{"group_id": "g1", "group_title_zh": "A"}])
    _write_jsonl(tmp_path / "ai.jsonl", [{"group_id": "g1", "group_title_zh": "A"}, {"group_id": "g2", "group_title_zh": "B"}])
    groups = load_reviewed_groups("combined")
    ids = [g["group_id"] for g in groups]
    assert len(set(ids)) == len(ids)


def test_unknown_source_raises():
    with pytest.raises(ValueError):
        load_reviewed_groups("nonexistent_source")


def test_resolve_source_type_label():
    assert resolve_source_type_label("calibrated_llm") == "calibrated_llm_ai_reviewed_group"
    assert resolve_source_type_label("llm") == "llm_ai_reviewed_group"
    assert resolve_source_type_label("ai") == "ai_reviewed_group"
    assert resolve_source_type_label("human") == "human_reviewed_group"
    assert resolve_source_type_label("unknown") == "unknown"


def test_empty_source_returns_empty(tmp_path, monkeypatch):
    import demand_radar.truth_scoring.truth_input_loader as loader
    monkeypatch.setattr(loader, "SOURCE_PATHS", {
        "calibrated_llm": tmp_path / "missing.jsonl",
        "llm": tmp_path / "missing2.jsonl",
        "ai": tmp_path / "missing3.jsonl",
        "human": tmp_path / "missing4.jsonl",
    })
    groups = load_reviewed_groups("auto")
    assert groups == []
