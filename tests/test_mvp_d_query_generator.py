from demand_radar.mvp_d.query_generator import build_seeded_query_plan_report, generate_queries
from demand_radar.mvp_d.seed_schema import ReviewedPainSeed


def _seed():
    return ReviewedPainSeed(
        seed_id="seed_001",
        pain_item_id="pain__000022",
        candidate_id="cand_022",
        title="Seed A",
        source_url="https://news.ycombinator.com/item?id=1",
        persona="VC analyst",
        workflow_stage="deal_sourcing",
        pain_type="manual_workflow",
        pain_description_zh="manual workflow",
        evidence_quote="quote",
        true_pain=True,
        commercial_potential="medium",
        evidence_quality="strong",
        action_decision="needs_more_evidence",
        expansion_priority="high",
        seed_reason_zh="true pain",
        created_at="2026-01-01T00:00:00Z",
    )


def test_generate_queries_keeps_seed_links(tmp_path):
    queries = generate_queries(
        [_seed()],
        output_path=tmp_path / "queries.jsonl",
        report_path=tmp_path / "seeded_query_plan_report.md",
        max_queries_total=6,
    )
    assert queries
    assert all(q.seed_id == "seed_001" for q in queries)
    assert all(q.pain_item_id == "pain__000022" for q in queries)
    assert any(q.query_type == "persona_workflow" for q in queries)
    assert any(q.connector in {"hacker_news", "github_issues", "rss"} for q in queries)
    assert (tmp_path / "seeded_query_plan_report.md").exists()

