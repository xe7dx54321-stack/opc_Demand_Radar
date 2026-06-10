from demand_radar.config.schemas import NormalizedSignal
from demand_radar.extraction.rule_based_extractor import RuleBasedPainExtractor


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


def test_keyword_text_extracts_pain_point() -> None:
    extractor = RuleBasedPainExtractor()
    signal = make_signal("Developer API workflow is frustrating and slow every week.")

    candidate = extractor.extract(signal, "pain_000001", {})

    assert candidate["evidence_quote"] == "Developer API workflow is frustrating and slow every week."
    assert candidate["persona"] == "developer"
    assert candidate["extraction_mode"] == "rule_based"
    assert 0 <= float(candidate["confidence"]) <= 1


def test_text_without_pain_keyword_has_no_evidence_quote() -> None:
    extractor = RuleBasedPainExtractor()
    signal = make_signal("The product launched a new page today.")

    candidate = extractor.extract(signal, "pain_000001", {})

    assert candidate["evidence_quote"] == ""
    assert candidate["confidence"] == 0.2


def test_chinese_keyword_text_extracts_pain_point() -> None:
    extractor = RuleBasedPainExtractor()
    signal = make_signal("\u5185\u5bb9\u56e2\u961f\u6bcf\u5468\u9009\u9898\u5f88\u96be\uff0c\u4fe1\u606f\u592a\u5206\u6563\u3002")

    candidate = extractor.extract(signal, "pain_000001", {})

    assert candidate["evidence_quote"]
    assert candidate["persona"] == "content_team"

