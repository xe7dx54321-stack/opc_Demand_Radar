from demand_radar.mvp_d2.calibrated_query_generator import build_calibrated_query_plan
from tests.test_mvp_d2_fixtures import write_d2_fixture


def test_calibrated_query_plan_keeps_seed_and_pain_type(tmp_path):
    paths = write_d2_fixture(tmp_path, count=2)
    queries = build_calibrated_query_plan(
        seed_profiles_path=paths["seeds"],
        output_path=tmp_path / "calibrated_query_plan_v2.jsonl",
        report_path=tmp_path / "calibrated_query_plan_report.md",
        max_queries=12,
    )

    assert queries
    assert all(query.seed_id == "seed_1" for query in queries)
    assert all(query.pain_item_id == "pain_seed_1" for query in queries)
    assert any(query.query_type in {"pain_phrase", "manual_workflow", "workaround_phrase"} for query in queries)
    assert any("spreadsheet" in query.query.lower() or "manual" in query.query.lower() for query in queries)
    assert not all("tool" in query.query.lower() for query in queries)
    assert (tmp_path / "calibrated_query_plan_report.md").exists()
