from demand_radar.config.schemas import NormalizedSignal
from demand_radar.extraction.llm_extractor_stub import LLMExtractorStub
from demand_radar.state.state_gate import pain_point_gate


def make_signal(text: str) -> NormalizedSignal:
    return NormalizedSignal(
        raw_signal_id="sig_000001",
        normalized_signal_id="norm_000001",
        source_name="manual_import",
        title="Signal title",
        normalized_text=text,
        url=None,
        language="en",
        domain_tags=["ai_agent_workflow"],
        content_hash="abc",
    )


def test_llm_extractor_stub_returns_empty_list_by_default() -> None:
    extractor = LLMExtractorStub()

    assert extractor.extract(make_signal("No concrete pain."), "pain_000001", {}) == []


def test_llm_extractor_stub_returns_fixture_candidates() -> None:
    extractor = LLMExtractorStub(
        [
            {
                "pain_description": "manual tracking is hard",
                "evidence_quote": "manual tracking is hard",
                "confidence": 0.8,
            }
        ]
    )

    candidates = extractor.extract(make_signal("manual tracking is hard"), "pain_000001", {})

    assert len(candidates) == 1
    assert candidates[0]["raw_signal_id"] == "sig_000001"
    assert candidates[0]["extraction_mode"] == "llm_stub"


def test_llm_stub_invalid_candidate_is_blocked_by_state_gate() -> None:
    extractor = LLMExtractorStub(
        [
            {
                "pain_description": "invented pain",
                "evidence_quote": "not in source",
                "confidence": 0.9,
            }
        ]
    )
    signal = make_signal("manual tracking is hard")
    candidate = extractor.extract(signal, "pain_000001", {})[0]

    result = pain_point_gate(candidate, signal.normalized_text)

    assert not result.passed
    assert result.reason == "evidence_quote_not_found"
