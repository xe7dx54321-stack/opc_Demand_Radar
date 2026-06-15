"""Tests for Stage 3.4 lineage_store."""
import json
import pytest
from pathlib import Path
from datetime import datetime, timezone
from demand_radar.lineage.lineage_schema import (
    CandidateLineage, TargetedEvidenceAttribution, StableTruthScoreDelta
)
from demand_radar.lineage.lineage_store import (
    write_candidate_lineage, load_candidate_lineage,
    write_targeted_evidence_attribution, load_targeted_evidence_attribution,
    write_stable_truth_score_delta, load_stable_truth_score_delta,
)

NOW = datetime.now(timezone.utc).isoformat()


def _lineage(lid):
    return CandidateLineage(
        lineage_id=lid, match_score=0.8, match_strength="strong",
        lineage_summary_zh="test", created_at=NOW
    )


def _attribution(aid, status="attributed_to_expected_group"):
    return TargetedEvidenceAttribution(
        attribution_id=aid, target_signal_id="tsig_001",
        attribution_status=status, attribution_confidence=0.9,
        attribution_reason_zh="test", created_at=NOW
    )


def _stable_delta(did):
    return StableTruthScoreDelta(
        stable_delta_id=did, lineage_id="lin_001",
        before_truth_score=60.0, after_truth_score=72.0, stable_delta=12.0,
        delta_confidence="high", interpretation_zh="test",
        recommended_next_action="keep_watch", created_at=NOW
    )


def test_write_load_candidate_lineage(tmp_path):
    path = tmp_path / "lineage.jsonl"
    items = [_lineage("l1"), _lineage("l2")]
    write_candidate_lineage(items, path=str(path))
    loaded = load_candidate_lineage(path=str(path))
    assert len(loaded) == 2
    assert loaded[0].lineage_id == "l1"
    assert loaded[1].lineage_id == "l2"


def test_load_empty_lineage(tmp_path):
    path = tmp_path / "empty.jsonl"
    assert load_candidate_lineage(path=str(path)) == []


def test_write_load_attribution(tmp_path):
    path = tmp_path / "attr.jsonl"
    items = [_attribution("a1"), _attribution("a2", "lost_in_extraction")]
    write_targeted_evidence_attribution(items, path=str(path))
    loaded = load_targeted_evidence_attribution(path=str(path))
    assert len(loaded) == 2
    assert loaded[1].attribution_status == "lost_in_extraction"


def test_write_load_stable_delta(tmp_path):
    path = tmp_path / "delta.jsonl"
    items = [_stable_delta("sd1")]
    write_stable_truth_score_delta(items, path=str(path))
    loaded = load_stable_truth_score_delta(path=str(path))
    assert len(loaded) == 1
    assert loaded[0].stable_delta == pytest.approx(12.0)
    assert loaded[0].delta_confidence == "high"
