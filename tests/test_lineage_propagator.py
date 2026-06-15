"""Tests for Stage 3.4 lineage_propagator."""
import json
import shutil
import pytest
from pathlib import Path
from demand_radar.lineage.lineage_propagator import (
    snapshot_truth_state,
    load_snapshot_truth_scores,
    load_current_truth_scores,
)

def _make_truth_score(gid, score):
    return {
        "truth_score_id": f"ts_{gid}",
        "source_group_id": gid,
        "group_title_zh": f"候选 {gid}",
        "truth_score": score,
        "truth_level": "medium",
        "recommended_next_action": "needs_more_evidence",
        "personas": ["operator"],
        "domain_tags": ["ai"],
    }


def test_snapshot_creates_directory(tmp_path):
    # Create a mock truth_scores.jsonl
    src_dir = tmp_path / "data" / "processed"
    src_dir.mkdir(parents=True)
    ts_path = src_dir / "truth_scores.jsonl"
    ts_path.write_text(
        json.dumps(_make_truth_score("grp_001", 65.0)) + "\n",
        encoding="utf-8"
    )
    archive_dir = tmp_path / "archive"
    dest = snapshot_truth_state(
        name="test_snapshot",
        sources={"truth_scores.jsonl": str(ts_path)},
        base_dir=str(archive_dir),
    )
    assert dest.exists()
    assert (dest / "truth_scores.jsonl").exists()
    manifest = json.loads((dest / "manifest.json").read_text())
    assert "truth_scores.jsonl" in manifest["files"]


def test_load_snapshot_truth_scores(tmp_path):
    snap_dir = tmp_path / "snap"
    snap_dir.mkdir()
    ts_path = snap_dir / "truth_scores.jsonl"
    ts_path.write_text(
        json.dumps(_make_truth_score("grp_001", 65.0)) + "\n"
        + json.dumps(_make_truth_score("grp_002", 58.0)) + "\n",
        encoding="utf-8",
    )
    scores = load_snapshot_truth_scores(snap_dir)
    assert len(scores) == 2
    assert scores[0]["truth_score"] == pytest.approx(65.0)


def test_load_snapshot_missing_dir(tmp_path):
    scores = load_snapshot_truth_scores(tmp_path / "nonexistent")
    assert scores == []


def test_load_current_truth_scores(tmp_path):
    ts_path = tmp_path / "truth_scores.jsonl"
    ts_path.write_text(
        json.dumps(_make_truth_score("grp_001", 70.0)) + "\n",
        encoding="utf-8",
    )
    scores = load_current_truth_scores(path=str(ts_path))
    assert len(scores) == 1
    assert scores[0]["group_title_zh"] == "候选 grp_001"
