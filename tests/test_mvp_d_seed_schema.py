from demand_radar.mvp_d.seed_schema import EvidenceTheme, ReviewedPainSeed, SeededQuery


def test_seed_schema_accepts_required_fields():
    seed = ReviewedPainSeed(
        seed_id="seed_001",
        pain_item_id="pain__000022",
        candidate_id="cand_001",
        source_url="https://news.ycombinator.com/item?id=1",
        true_pain=True,
        expansion_priority="high",
        seed_reason_zh="true pain",
        created_at="2026-01-01T00:00:00Z",
    )
    assert seed.true_pain is True
    assert seed.metadata == {}


def test_seeded_query_keeps_seed_metadata():
    query = SeededQuery(
        query_id="query_001",
        seed_id="seed_001",
        pain_item_id="pain__000022",
        connector="hacker_news",
        query='"VC analyst" "due diligence"',
        query_type="persona_workflow",
        expected_signal_type="pain",
        priority="high",
        created_at="2026-01-01T00:00:00Z",
    )
    assert query.seed_id == "seed_001"
    assert query.pain_item_id == "pain__000022"


def test_evidence_theme_defaults_are_not_shared():
    a = EvidenceTheme(
        theme_id="theme_1",
        theme_title_zh="主题",
        theme_summary_zh="摘要",
        evidence_count=1,
        reviewed_seed_count=1,
        new_evidence_count=0,
        commercial_potential="medium",
        confidence=0.5,
        action_recommendation="watch",
        created_at="2026-01-01T00:00:00Z",
    )
    b = EvidenceTheme(
        theme_id="theme_2",
        theme_title_zh="主题",
        theme_summary_zh="摘要",
        evidence_count=1,
        reviewed_seed_count=1,
        new_evidence_count=0,
        commercial_potential="medium",
        confidence=0.5,
        action_recommendation="watch",
        created_at="2026-01-01T00:00:00Z",
    )
    a.seed_ids.append("seed_1")
    assert b.seed_ids == []
