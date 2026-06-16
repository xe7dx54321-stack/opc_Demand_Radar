"""Tests for ExtractedPainItem schema."""
import pytest
from demand_radar.mvp_b.pain_extraction_schema import ExtractedPainItem


def _base(**kw):
    defaults = dict(
        pain_item_id="pain_001",
        candidate_id="cand_001",
        should_extract=True,
        evidence_quote="We spend hours manually tracking startups in spreadsheets.",
        evidence_strength="medium",
        confidence=0.75,
        created_at="2026-01-01T00:00:00Z",
    )
    defaults.update(kw)
    return defaults


def test_valid_extract():
    item = ExtractedPainItem(**_base())
    assert item.should_extract is True
    assert item.evidence_strength == "medium"


def test_reject_needs_reason():
    with pytest.raises(Exception):
        ExtractedPainItem(**_base(should_extract=False, evidence_quote=None, reject_reason=None))


def test_valid_reject():
    item = ExtractedPainItem(**_base(
        should_extract=False,
        evidence_quote=None,
        reject_reason="Not relevant to investment domain",
        evidence_strength="reject",
        confidence=0.0,
    ))
    assert item.should_extract is False
    assert item.reject_reason is not None


def test_extract_needs_quote():
    with pytest.raises(Exception):
        ExtractedPainItem(**_base(evidence_quote=None))


def test_confidence_out_of_range():
    with pytest.raises(Exception):
        ExtractedPainItem(**_base(confidence=1.5))


def test_confidence_negative_raises():
    with pytest.raises(Exception):
        ExtractedPainItem(**_base(confidence=-0.1))


def test_strong_needs_persona_and_workflow():
    with pytest.raises(Exception):
        ExtractedPainItem(**_base(
            evidence_strength="strong",
            persona=None,
            workflow_stage=None,
            pain_description_zh=None,
        ))


def test_strong_valid():
    item = ExtractedPainItem(**_base(
        evidence_strength="strong",
        persona="VC analyst",
        workflow_stage="deal_sourcing",
        pain_description_zh="Manually tracking AI startups is extremely time-consuming.",
    ))
    assert item.evidence_strength == "strong"


def test_optional_fields_none():
    item = ExtractedPainItem(**_base())
    assert item.persona is None
    assert item.current_solution is None
    assert item.commercial_signal_type is None
