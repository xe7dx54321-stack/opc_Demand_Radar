"""Tests for Stage 3.5 candidate selector."""
import json
import pytest
from pathlib import Path
from demand_radar.stage35.stage35_candidate_selector import select_stage35_candidates

NOW = "2026-01-01T00:00:00+00:00"


def _ts(gid, title, score=62.0, level="medium"):
    return json.dumps({
        "truth_score_id": f"ts_{gid}",
        "source_group_id": gid,
        "group_title_zh": title,
        "truth_score": score,
        "truth_level": level,
        "recommended_next_action": "needs_more_evidence",
    }, ensure_ascii=False)


def test_selects_preferred_candidates(tmp_path):
    ts_file = tmp_path / "truth_scores.jsonl"
    ts_file.write_text(
        _ts("g1", "投资人AI产业跟踪项目初筛", 62.0) + "\n" +
        _ts("g2", "企业知识工作流检索困难", 60.0) + "\n" +
        _ts("g3", "内容团队选题准备", 58.0) + "\n",
        encoding="utf-8"
    )
    out = tmp_path / "selected.jsonl"
    results = select_stage35_candidates(
        truth_scores_path=ts_file, max_candidates=2, output_path=out
    )
    titles = [r.group_title_zh for r in results]
    assert any("产业跟踪" in t or "项目初筛" in t for t in titles)
    assert not any("内容团队选题" in t for t in titles)


def test_excludes_content_candidates(tmp_path):
    ts_file = tmp_path / "truth_scores.jsonl"
    ts_file.write_text(
        _ts("g1", "内容团队选题准备工作", 70.0) + "\n" +
        _ts("g2", "AI Agent工作流可靠性", 65.0) + "\n",
        encoding="utf-8"
    )
    out = tmp_path / "selected.jsonl"
    results = select_stage35_candidates(truth_scores_path=ts_file, output_path=out)
    # Both should be excluded
    titles = [r.group_title_zh for r in results]
    assert not any("内容团队选题" in t for t in titles)
    assert not any("AI Agent" in t for t in titles)


def test_no_candidates_returns_empty(tmp_path):
    ts_file = tmp_path / "truth_scores.jsonl"
    ts_file.write_text("\n", encoding="utf-8")
    out = tmp_path / "selected.jsonl"
    results = select_stage35_candidates(truth_scores_path=ts_file, output_path=out)
    assert results == []


def test_max_candidates_respected(tmp_path):
    ts_file = tmp_path / "truth_scores.jsonl"
    lines = "\n".join(
        _ts(f"g{i}", f"企业知识工作流{i}", 60.0 + i)
        for i in range(5)
    )
    ts_file.write_text(lines + "\n", encoding="utf-8")
    out = tmp_path / "selected.jsonl"
    results = select_stage35_candidates(
        truth_scores_path=ts_file, max_candidates=2, output_path=out
    )
    assert len(results) <= 2


def test_output_file_written(tmp_path):
    ts_file = tmp_path / "truth_scores.jsonl"
    ts_file.write_text(
        _ts("g1", "企业知识工作流") + "\n",
        encoding="utf-8"
    )
    out = tmp_path / "selected.jsonl"
    select_stage35_candidates(truth_scores_path=ts_file, output_path=out)
    assert out.exists()
