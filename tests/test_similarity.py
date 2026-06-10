from demand_radar.clustering.similarity import pain_point_similarity, text_similarity
from demand_radar.config.schemas import PainPoint


def make_pain(
    pain_point_id: str,
    pain_description: str,
    persona: str = "investor",
    job_to_be_done: str | None = "track AI company updates",
    current_workaround: str | None = "manual spreadsheet",
) -> PainPoint:
    return PainPoint(
        pain_point_id=pain_point_id,
        raw_signal_id=f"sig_{pain_point_id[-6:]}",
        normalized_signal_id=f"norm_{pain_point_id[-6:]}",
        persona=persona,
        scenario="tracking AI companies",
        job_to_be_done=job_to_be_done,
        current_workaround=current_workaround,
        pain_description=pain_description,
        pain_intensity=4,
        frequency_signal="weekly",
        payment_signal=None,
        evidence_quote=pain_description,
        evidence_span=pain_description,
        confidence=0.8,
        extraction_mode="rule_based",
        extraction_notes=None,
    )


def test_text_similarity_scores_related_text_higher_than_unrelated_text() -> None:
    related = text_similarity("manual tracking is slow", "manual tracking is too slow")
    unrelated = text_similarity("manual tracking is slow", "newsletter topic planning")

    assert related > unrelated
    assert related > 70


def test_pain_point_similarity_uses_persona_and_task_fields() -> None:
    left = make_pain("pain_000001", "manual AI company tracking is slow")
    related = make_pain("pain_000002", "manual AI company tracking is too slow")
    unrelated = make_pain(
        "pain_000003",
        "developer API docs are incomplete",
        persona="developer",
        job_to_be_done="find SDK examples",
        current_workaround="search old GitHub issues",
    )

    assert pain_point_similarity(left, related).total > pain_point_similarity(left, unrelated).total
