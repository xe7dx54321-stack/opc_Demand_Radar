from demand_radar.mvp_d2.calibrated_query_generator import build_calibrated_query_plan_report
from demand_radar.mvp_d2.mvp_d2_report import build_mvp_d2_summary_report
from demand_radar.mvp_d2.reject_diagnostics_schema import MVPD2RunSummary
from tests.test_mvp_d2_fixtures import write_d2_fixture


def test_mvp_d2_reports_can_generate(tmp_path):
    paths = write_d2_fixture(tmp_path, count=1)
    from demand_radar.mvp_d2.calibrated_query_generator import build_calibrated_query_plan

    queries = build_calibrated_query_plan(
        seed_profiles_path=paths["seeds"],
        output_path=tmp_path / "queries_v2.jsonl",
        report_path=tmp_path / "query_report.md",
    )
    report = build_calibrated_query_plan_report(queries, tmp_path / "query_report_2.md")
    assert report.exists()

    summary = MVPD2RunSummary(
        domain_id="ai_investment_tracking",
        generated_at="2026-01-01T00:00:00Z",
        mvp_d_selected_for_llm=28,
        mvp_d_should_extract_true=0,
        mvp_d_reject_count=28,
        total_rejected=28,
        generated_v2_queries=len(queries),
        ran_pilot=False,
        blocked_reason="blocked_by_missing_search_provider",
        comparison_result="blocked",
        engineering_acceptance="pass",
        product_acceptance="partial",
        can_rerun_seeded_expansion=True,
        can_enter_second_review=False,
        can_enter_foundation_source_upgrade=True,
        reason="blocked",
        metadata={
            "by_reject_category": {"domain_out": 1},
            "source_quality_scores": {"github_issue": 0.1},
            "query_types": {"pain_phrase": 1},
            "example_queries": [queries[0].query],
        },
    )
    path = build_mvp_d2_summary_report(summary, tmp_path / "summary.md")
    assert path.exists()
    assert "MVP-D2" in path.read_text(encoding="utf-8")

