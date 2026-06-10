from demand_radar.config.schemas import PainPoint
from demand_radar.state.state_gate import pain_point_gate


def make_pain_point(**overrides: object) -> PainPoint:
    payload = {
        "pain_point_id": "pain_000001",
        "raw_signal_id": "sig_000001",
        "normalized_signal_id": "norm_000001",
        "persona": "researcher",
        "scenario": "tracking updates",
        "job_to_be_done": "track updates",
        "current_workaround": "manual work",
        "pain_description": "manual tracking is frustrating",
        "pain_intensity": 4,
        "frequency_signal": "weekly",
        "payment_signal": "labor/time cost signal mentioned",
        "evidence_quote": "manual tracking is frustrating",
        "evidence_span": "manual tracking is frustrating",
        "confidence": 0.82,
        "extraction_mode": "rule_based",
        "extraction_notes": "test",
    }
    payload.update(overrides)
    return PainPoint.model_validate(payload)


def test_missing_evidence_quote_fails() -> None:
    candidate = make_pain_point().model_dump(mode="json")
    candidate["evidence_quote"] = ""

    result = pain_point_gate(candidate, "manual tracking is frustrating")

    assert not result.passed
    assert result.reason == "missing_evidence_quote"


def test_evidence_quote_not_in_source_fails() -> None:
    result = pain_point_gate(make_pain_point(), "different source text")

    assert not result.passed
    assert result.reason == "evidence_quote_not_found"


def test_low_confidence_fails() -> None:
    result = pain_point_gate(make_pain_point(confidence=0.4), "manual tracking is frustrating")

    assert not result.passed
    assert result.reason == "low_confidence"


def test_valid_pain_point_passes() -> None:
    result = pain_point_gate(make_pain_point(), "The team says manual tracking is frustrating.")

    assert result.passed
    assert result.reason is None

