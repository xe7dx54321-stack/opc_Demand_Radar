from demand_radar.mvp_d2.source_quality_analyzer import (
    analyze_source_quality,
    recommend_source_strategy,
)
from tests.test_mvp_d2_fixtures import write_d2_fixture


def test_source_quality_yield_rate_and_recommendation(tmp_path):
    paths = write_d2_fixture(tmp_path, count=4)
    scores, summary = analyze_source_quality(
        candidates_path=paths["candidates"],
        pain_items_path=paths["pain_items"],
        diagnostics_path=tmp_path / "missing.jsonl",
        output_path=tmp_path / "source_quality_scores.jsonl",
        report_path=tmp_path / "source_quality_report.md",
    )

    assert scores
    assert all(score.yield_rate == 0 for score in scores)
    github = [score for score in scores if score.source_type == "github_issue"][0]
    assert github.source_strategy_recommendation != "keep"
    assert summary["needs_better_query"] or summary["use_only_for_context"]
    assert (tmp_path / "source_quality_report.md").exists()


def test_github_all_rejected_is_not_keep():
    assert recommend_source_strategy(
        source_type="github_issue",
        connector="github_issues",
        yield_rate=0,
        llm_processed=10,
        reject_count=10,
        dominant_reject_reason="technical_issue_not_business_pain",
    ) == "use_only_for_context"

