from demand_radar.ui.mvp_d2_service import get_mvp_d2_overview
from tests.test_mvp_d2_fixtures import write_jsonl


def test_mvp_d2_ui_service_reads_overview(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_jsonl(
        tmp_path / "data/processed/mvp_d2/reject_diagnostics.jsonl",
        [{"diagnostic_id": "d1", "candidate_id": "c1", "reject_category": "domain_out"}],
    )
    write_jsonl(
        tmp_path / "data/processed/mvp_d2/source_quality_scores.jsonl",
        [{"score_id": "s1", "source_type": "github_issue", "source_strategy_recommendation": "needs_better_query"}],
    )
    write_jsonl(
        tmp_path / "data/processed/mvp_d2/calibrated_query_plan_v2.jsonl",
        [{"query_id": "q1", "query_type": "pain_phrase", "query": '"workflow" "pain"'}],
    )
    (tmp_path / "outputs/mvp_d2").mkdir(parents=True)
    (tmp_path / "outputs/mvp_d2/calibrated_expansion_report.md").write_text(
        "- ran_pilot: false\n- blocked_reason: blocked_by_missing_search_provider\n- should_extract_true: 0\n- yield_rate: 0.0\n",
        encoding="utf-8",
    )
    (tmp_path / "outputs/mvp_d2/d2_comparison_report.md").write_text(
        "- result: blocked\n",
        encoding="utf-8",
    )
    (tmp_path / "outputs/mvp_d2/mvp_d2_summary_report.md").write_text(
        "- engineering_acceptance: pass\n- product_acceptance: partial\n- reason: ok\n",
        encoding="utf-8",
    )

    overview = get_mvp_d2_overview()
    assert overview["total_rejected"] == 1
    assert overview["v2_queries"] == 1
    assert overview["comparison_result"] == "blocked"
    assert overview["engineering_acceptance"] == "pass"
