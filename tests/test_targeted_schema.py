"""Tests for Stage 3.3 targeted_schema."""
import pytest
from demand_radar.targeted_expansion.targeted_schema import (
    TargetedSignalTemplateRow,
    TargetedSignalValidation,
    TruthScoreDelta,
    TargetedExpansionSummary,
)


def _make_row(**kwargs):
    defaults = dict(
        target_signal_id="tsig_000001",
        target_group_id="grp_001",
        target_group_title_zh="测试候选",
        evidence_intent="paid_alternative",
        collection_status="pending",
    )
    defaults.update(kwargs)
    return TargetedSignalTemplateRow(**defaults)


def _make_validation(**kwargs):
    from datetime import datetime, timezone
    defaults = dict(
        validation_id="val_001",
        target_signal_id="tsig_000001",
        status="valid",
        include_in_combined_input=True,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    defaults.update(kwargs)
    return TargetedSignalValidation(**defaults)


def test_template_row_valid():
    row = _make_row()
    assert row.target_signal_id == "tsig_000001"
    assert row.collection_status == "pending"
    assert row.is_synthetic is False
    assert row.exclude_from_truth_scoring is False


def test_template_row_invalid_status():
    with pytest.raises(Exception):
        _make_row(collection_status="unknown_status")


def test_template_row_collected_status():
    row = _make_row(
        collection_status="collected",
        raw_text="Some real signal text about pricing.",
        url="https://example.com",
    )
    assert row.collection_status == "collected"


def test_validation_valid():
    v = _make_validation()
    assert v.status == "valid"
    assert v.include_in_combined_input is True


def test_validation_invalid_status():
    with pytest.raises(Exception):
        _make_validation(status="unknown_status")


def test_validation_excluded_not_in_combined():
    v = _make_validation(status="excluded", include_in_combined_input=False)
    assert v.include_in_combined_input is False


def test_truth_score_delta_fields():
    from datetime import datetime, timezone
    delta = TruthScoreDelta(
        source_group_id="grp_001",
        group_title_zh="测试候选",
        before_truth_score=60.0,
        after_truth_score=72.5,
        delta=12.5,
        before_truth_level="medium",
        after_truth_level="medium",
        before_next_action="needs_more_evidence",
        after_next_action="needs_more_evidence",
        improved_dimensions=["willingness_to_pay"],
        remaining_gaps=["frequency_repetition"],
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    assert delta.delta == pytest.approx(12.5)
    assert "willingness_to_pay" in delta.improved_dimensions


def test_expansion_summary_defaults():
    from datetime import datetime, timezone
    summary = TargetedExpansionSummary(
        created_at=datetime.now(timezone.utc).isoformat()
    )
    assert summary.template_rows == 0
    assert summary.valid_signals == 0


def test_all_evidence_intents():
    from demand_radar.targeted_expansion.targeted_schema import VALID_EVIDENCE_INTENTS
    assert "paid_alternative" in VALID_EVIDENCE_INTENTS
    assert "budget_signal" in VALID_EVIDENCE_INTENTS
    assert "manual_workaround" in VALID_EVIDENCE_INTENTS
    assert "business_impact" in VALID_EVIDENCE_INTENTS
    assert "time_cost" in VALID_EVIDENCE_INTENTS
