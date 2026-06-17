import json

from demand_radar.mvp_d2.d2_comparison import compare_expansion_v1_v2, compare_yield
from tests.test_mvp_d2_fixtures import write_jsonl


def test_v1_v2_comparison_improved_and_blocked(tmp_path):
    (tmp_path / "outputs/mvp_d").mkdir(parents=True)
    (tmp_path / "outputs/mvp_d2").mkdir(parents=True)
    (tmp_path / "data/processed/mvp_d").mkdir(parents=True)
    (tmp_path / "data/processed/mvp_d2").mkdir(parents=True)
    (tmp_path / "outputs/mvp_d/expansion_pain_extraction_report.md").write_text(
        "- total_candidates: 10\n- selected_for_llm: 10\n- allowed_by_gate: 10\n- should_extract_true: 0\n- status: completed\n",
        encoding="utf-8",
    )
    write_jsonl(tmp_path / "data/processed/mvp_d/seeded_query_plan.jsonl", [{"query_id": "q1"}])
    write_jsonl(tmp_path / "data/processed/mvp_d/expansion_evidence_candidates.jsonl", [{"candidate_id": "c1"}])
    (tmp_path / "outputs/mvp_d2/calibrated_expansion_report.md").write_text(
        "- status: completed\n- blocked_reason: n/a\n- raw_new_signals: 5\n- unique_new_signals: 5\n- gate_allowed: 5\n- selected_for_llm: 5\n- should_extract_true: 1\n- yield_rate: 0.2\n",
        encoding="utf-8",
    )
    write_jsonl(tmp_path / "data/processed/mvp_d2/calibrated_query_plan_v2.jsonl", [{"query_id": "q2"}])
    payload = compare_expansion_v1_v2(
        v1_report_path=tmp_path / "outputs/mvp_d/expansion_pain_extraction_report.md",
        v1_query_plan_path=tmp_path / "data/processed/mvp_d/seeded_query_plan.jsonl",
        v1_candidates_path=tmp_path / "data/processed/mvp_d/expansion_evidence_candidates.jsonl",
        v2_report_path=tmp_path / "outputs/mvp_d2/calibrated_expansion_report.md",
        v2_query_plan_path=tmp_path / "data/processed/mvp_d2/calibrated_query_plan_v2.jsonl",
        report_path=tmp_path / "outputs/mvp_d2/d2_comparison_report.md",
    )

    assert payload["result"] == "improved"
    assert (tmp_path / "outputs/mvp_d2/d2_comparison_report.md").exists()
    assert compare_yield({"yield_rate": 0}, {"status": "blocked", "blocked_reason": "x"}) == "blocked"

