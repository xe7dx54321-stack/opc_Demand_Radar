"""Tests for Stage 3.4 lineage_service (UI layer)."""
import pytest
from datetime import datetime, timezone
from demand_radar.lineage.lineage_schema import (
    CandidateLineage, TargetedEvidenceAttribution, StableTruthScoreDelta
)
from demand_radar.lineage import lineage_store
from demand_radar.ui import lineage_service

NOW = datetime.now(timezone.utc).isoformat()


def _lineage(lid):
    return CandidateLineage(
        lineage_id=lid,
        match_strength="weak",
        match_score=0.6,
        lineage_summary_zh="test",
        created_at=NOW,
    )


def _attr(aid):
    return TargetedEvidenceAttribution(
        attribution_id=aid,
        target_signal_id=f"tsig_{aid}",
        attribution_status="attributed_to_expected_group",
        attribution_confidence=0.8,
        attribution_reason_zh="test",
        created_at=NOW,
    )


def _delta(did):
    return StableTruthScoreDelta(
        stable_delta_id=did,
        lineage_id="l1",
        delta_confidence="medium",
        interpretation_zh="test",
        recommended_next_action="keep_watch",
        created_at=NOW,
    )


def test_get_candidate_lineages_empty_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setattr(lineage_store, "LINEAGE_PATH", tmp_path / "nonexistent.jsonl")
    result = lineage_service.get_candidate_lineages()
    assert result == []


def test_get_candidate_lineages_returns_data(tmp_path, monkeypatch):
    items = [_lineage("l1"), _lineage("l2")]
    path = tmp_path / "lineage.jsonl"
    lineage_store.write_candidate_lineage(items, path=str(path))
    monkeypatch.setattr(lineage_store, "LINEAGE_PATH", path)
    result = lineage_service.get_candidate_lineages()
    assert len(result) == 2
    assert result[0].lineage_id == "l1"


def test_get_targeted_evidence_attributions_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(lineage_store, "ATTRIBUTION_PATH", tmp_path / "nonexistent.jsonl")
    result = lineage_service.get_targeted_evidence_attributions()
    assert result == []


def test_get_targeted_evidence_attributions_returns_data(tmp_path, monkeypatch):
    items = [_attr("a1"), _attr("a2"), _attr("a3")]
    path = tmp_path / "attr.jsonl"
    lineage_store.write_targeted_evidence_attribution(items, path=str(path))
    monkeypatch.setattr(lineage_store, "ATTRIBUTION_PATH", path)
    result = lineage_service.get_targeted_evidence_attributions()
    assert len(result) == 3


def test_get_stable_truth_score_deltas_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(lineage_store, "STABLE_DELTA_PATH", tmp_path / "nonexistent.jsonl")
    result = lineage_service.get_stable_truth_score_deltas()
    assert result == []


def test_get_stable_truth_score_deltas_returns_data(tmp_path, monkeypatch):
    items = [_delta("d1")]
    path = tmp_path / "delta.jsonl"
    lineage_store.write_stable_truth_score_delta(items, path=str(path))
    monkeypatch.setattr(lineage_store, "STABLE_DELTA_PATH", path)
    result = lineage_service.get_stable_truth_score_deltas()
    assert len(result) == 1
    assert result[0].delta_confidence == "medium"
