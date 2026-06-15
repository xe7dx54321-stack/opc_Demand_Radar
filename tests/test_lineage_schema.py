"""Tests for Stage 3.4 lineage_schema."""
import pytest
from datetime import datetime, timezone
from demand_radar.lineage.lineage_schema import (
    CandidateLineage, TargetedEvidenceAttribution, StableTruthScoreDelta
)

NOW = datetime.now(timezone.utc).isoformat()


def test_candidate_lineage_valid():
    lin = CandidateLineage(
        lineage_id="lineage_001",
        before_group_id="grp_before",
        before_group_title_zh="扩展前候选",
        before_truth_score=62.0,
        before_truth_level="medium",
        after_group_id="grp_after",
        after_group_title_zh="扩展后候选",
        after_truth_score=70.0,
        after_truth_level="medium",
        match_score=0.80,
        match_strength="strong",
        lineage_summary_zh="高置信匹配",
        created_at=NOW,
    )
    assert lin.match_strength == "strong"
    assert lin.match_score == pytest.approx(0.80)


def test_candidate_lineage_invalid_strength():
    with pytest.raises(Exception):
        CandidateLineage(
            lineage_id="l1",
            match_score=0.5,
            match_strength="unknown_strength",
            lineage_summary_zh="test",
            created_at=NOW,
        )


def test_targeted_evidence_attribution_valid():
    attr = TargetedEvidenceAttribution(
        attribution_id="attr_001",
        target_signal_id="tsig_001",
        target_group_id="grp_001",
        evidence_intent="paid_alternative",
        attribution_status="attributed_to_expected_group",
        attribution_confidence=0.9,
        attribution_reason_zh="进入预期 group",
        created_at=NOW,
    )
    assert attr.attribution_status == "attributed_to_expected_group"


def test_targeted_evidence_attribution_invalid_status():
    with pytest.raises(Exception):
        TargetedEvidenceAttribution(
            attribution_id="a1",
            target_signal_id="t1",
            attribution_status="bad_status",
            attribution_confidence=0.5,
            attribution_reason_zh="test",
            created_at=NOW,
        )


def test_stable_truth_score_delta_valid():
    delta = StableTruthScoreDelta(
        stable_delta_id="sd_001",
        lineage_id="lineage_001",
        before_truth_score=60.0,
        after_truth_score=72.0,
        stable_delta=12.0,
        before_truth_level="medium",
        after_truth_level="medium",
        delta_confidence="high",
        interpretation_zh="高置信 delta",
        recommended_next_action="collect_more_targeted_evidence",
        created_at=NOW,
    )
    assert delta.stable_delta == pytest.approx(12.0)
    assert delta.delta_confidence == "high"


def test_stable_delta_invalid_confidence():
    with pytest.raises(Exception):
        StableTruthScoreDelta(
            stable_delta_id="sd_001",
            lineage_id="l1",
            delta_confidence="very_high",
            interpretation_zh="test",
            recommended_next_action="keep_watch",
            created_at=NOW,
        )


def test_stable_delta_invalid_action():
    with pytest.raises(Exception):
        StableTruthScoreDelta(
            stable_delta_id="sd_001",
            lineage_id="l1",
            delta_confidence="high",
            interpretation_zh="test",
            recommended_next_action="go_to_market",
            created_at=NOW,
        )


def test_all_match_strengths():
    from demand_radar.lineage.lineage_schema import VALID_MATCH_STRENGTHS
    assert "strong" in VALID_MATCH_STRENGTHS
    assert "weak" in VALID_MATCH_STRENGTHS
    assert "split" in VALID_MATCH_STRENGTHS
    assert "merged" in VALID_MATCH_STRENGTHS
    assert "unmatched" in VALID_MATCH_STRENGTHS
    assert "missing_baseline" in VALID_MATCH_STRENGTHS
