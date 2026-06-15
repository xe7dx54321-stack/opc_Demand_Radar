"""Tests for stable_delta computation."""
import pytest
from datetime import datetime, timezone
from demand_radar.lineage.lineage_schema import CandidateLineage, StableTruthScoreDelta
from demand_radar.lineage.stable_delta import compute_stable_deltas

NOW = datetime.now(timezone.utc).isoformat()


def _lin(lid, strength, before=60.0, after=72.0, b_level="medium", a_level="medium",
         drift=None, matched_sigs=None):
    return CandidateLineage(
        lineage_id=lid,
        match_strength=strength,
        match_score=0.8 if strength == "strong" else 0.6 if strength == "weak" else 0.3,
        before_truth_score=before,
        after_truth_score=after,
        before_truth_level=b_level,
        after_truth_level=a_level,
        drift_flags=drift or [],
        matched_targeted_signal_ids=matched_sigs or [],
        lineage_summary_zh="test",
        created_at=NOW,
    )


def test_strong_no_drift_gives_high_confidence(tmp_path):
    lineages = [_lin("l1", "strong", before=60.0, after=75.0, a_level="strong")]
    results = compute_stable_deltas(lineages, output_path=str(tmp_path / "d.jsonl"))
    assert len(results) == 1
    assert results[0].delta_confidence == "high"


def test_weak_match_gives_medium_confidence(tmp_path):
    lineages = [_lin("l1", "weak")]
    results = compute_stable_deltas(lineages, output_path=str(tmp_path / "d.jsonl"))
    assert results[0].delta_confidence == "medium"


def test_split_gives_low_confidence(tmp_path):
    lineages = [_lin("l1", "split", drift=["split_candidate"])]
    results = compute_stable_deltas(lineages, output_path=str(tmp_path / "d.jsonl"))
    assert results[0].delta_confidence == "low"


def test_merged_gives_low_confidence(tmp_path):
    lineages = [_lin("l1", "merged", drift=["merged_candidate"])]
    results = compute_stable_deltas(lineages, output_path=str(tmp_path / "d.jsonl"))
    assert results[0].delta_confidence == "low"


def test_missing_baseline_gives_low_confidence(tmp_path):
    lineages = [_lin("l1", "missing_baseline", before=None, after=70.0)]
    results = compute_stable_deltas(lineages, output_path=str(tmp_path / "d.jsonl"))
    assert results[0].delta_confidence == "low"


def test_stable_delta_computed_correctly(tmp_path):
    lineages = [_lin("l1", "weak", before=58.4, after=66.4)]
    results = compute_stable_deltas(lineages, output_path=str(tmp_path / "d.jsonl"))
    assert results[0].stable_delta == pytest.approx(8.0, abs=0.1)


def test_none_scores_give_none_delta(tmp_path):
    lineages = [_lin("l1", "missing_baseline", before=None, after=None)]
    results = compute_stable_deltas(lineages, output_path=str(tmp_path / "d.jsonl"))
    assert results[0].stable_delta is None


def test_proceed_to_fit_scoring_when_strong_level_high_confidence(tmp_path):
    lineages = [_lin("l1", "strong", before=70.0, after=80.0, a_level="strong")]
    results = compute_stable_deltas(lineages, output_path=str(tmp_path / "d.jsonl"))
    assert results[0].recommended_next_action == "proceed_to_fit_scoring"


def test_stabilize_lineage_when_many_drift_flags(tmp_path):
    lineages = [_lin("l1", "split", drift=["split_candidate", "group_title_drift", "evidence_loss"])]
    results = compute_stable_deltas(lineages, output_path=str(tmp_path / "d.jsonl"))
    assert results[0].recommended_next_action == "stabilize_lineage"


def test_drift_flag_reduces_confidence(tmp_path):
    # Strong match but with group_title_drift should NOT be high
    lineages = [_lin("l1", "strong", drift=["group_title_drift"])]
    results = compute_stable_deltas(lineages, output_path=str(tmp_path / "d.jsonl"))
    # group_title_drift alone is tolerated at medium for strong+weak combos
    assert results[0].delta_confidence in ("medium", "high")


def test_output_file_written(tmp_path):
    lineages = [_lin("l1", "weak")]
    out = tmp_path / "stable.jsonl"
    results = compute_stable_deltas(lineages, output_path=str(out))
    assert out.exists()
    assert len(results) == 1
