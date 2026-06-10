from demand_radar.config.schemas import NormalizedSignal
from demand_radar.extraction.rule_based_extractor import MAX_EVIDENCE_QUOTE_CHARS, RuleBasedPainExtractor


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


def extract_first(text: str) -> dict[str, object]:
    return RuleBasedPainExtractor().extract(make_signal(text), "pain_000001", {})[0]


def test_new_english_keywords_match() -> None:
    candidate = extract_first("VC teams can't keep up with AI infra updates because signals are scattered across sources.")

    assert candidate["evidence_quote"]
    assert candidate["persona"] == "investor"


def test_new_chinese_keywords_match() -> None:
    candidate = extract_first("\u7814\u7a76\u5458\u53cd\u9988\u4fe1\u606f\u592a\u4e71\uff0c\u4eba\u5de5\u6574\u7406\u5f88\u8d39\u65f6\u95f4\u3002")

    assert candidate["evidence_quote"]
    assert candidate["persona"] == "researcher"


def test_persona_operator_rule_matches() -> None:
    candidate = extract_first("Operator SOP workflow updates are too noisy and the manual process wastes time.")

    assert candidate["persona"] == "operator"


def test_evidence_quote_is_source_substring_and_length_limited() -> None:
    long_tail = "x" * 400
    text = f"Context sentence. Manual process is broken and hard to verify because docs are scattered. {long_tail}"
    candidate = extract_first(text)
    quote = str(candidate["evidence_quote"])

    assert quote in text
    assert len(quote) <= MAX_EVIDENCE_QUOTE_CHARS


def test_short_keyword_sentence_merges_with_neighbor_as_source_substring() -> None:
    text = "The analyst tracks pricing pages every week. Too noisy. They still use a spreadsheet."
    candidate = extract_first(text)
    quote = str(candidate["evidence_quote"])

    assert quote in text
    assert "Too noisy." in quote
