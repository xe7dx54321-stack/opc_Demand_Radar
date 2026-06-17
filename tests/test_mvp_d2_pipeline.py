from demand_radar.mvp_d2.mvp_d2_pipeline import run_mvp_d2
from tests.test_mvp_d2_fixtures import write_d2_fixture


def test_mvp_d2_pipeline_graceful_blocked_pilot(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs/expansion_diagnostics_config.yaml").write_text(
        """
expansion_diagnostics:
  input:
    expansion_candidates_path: candidates.jsonl
    expansion_pain_items_path: pain.jsonl
    seed_profiles_path: seeds.jsonl
    query_plan_path: queries.jsonl
  output:
    reject_diagnostics_path: data/processed/mvp_d2/reject_diagnostics.jsonl
    source_quality_scores_path: data/processed/mvp_d2/source_quality_scores.jsonl
    reject_diagnostics_report_path: outputs/mvp_d2/reject_diagnostics_report.md
    source_quality_report_path: outputs/mvp_d2/source_quality_report.md
""",
        encoding="utf-8",
    )
    (tmp_path / "configs/query_calibration_config.yaml").write_text(
        """
query_calibration:
  input:
    seed_profiles_path: seeds.jsonl
  output:
    calibrated_query_plan_path: data/processed/mvp_d2/calibrated_query_plan_v2.jsonl
    calibrated_candidates_path: data/processed/mvp_d2/calibrated_expansion_candidates.jsonl
    calibrated_pain_items_path: data/processed/mvp_d2/calibrated_expansion_pain_items.jsonl
    calibrated_expansion_report_path: outputs/mvp_d2/calibrated_expansion_report.md
    d2_comparison_report_path: outputs/mvp_d2/d2_comparison_report.md
    d2_summary_report_path: outputs/mvp_d2/mvp_d2_summary_report.md
  query_generation:
    max_queries_per_seed: 12
    min_queries_per_seed: 6
    max_total_queries: 48
  pilot:
    run_calibrated_pilot: true
""",
        encoding="utf-8",
    )
    paths = write_d2_fixture(tmp_path, count=3)
    # Files are already named candidates.jsonl/pain.jsonl/etc by config expectation.
    for source, target in [
        (paths["candidates"], tmp_path / "candidates.jsonl"),
        (paths["pain_items"], tmp_path / "pain.jsonl"),
        (paths["seeds"], tmp_path / "seeds.jsonl"),
        (paths["queries"], tmp_path / "queries.jsonl"),
    ]:
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "outputs/mvp_d").mkdir(parents=True)
    (tmp_path / "outputs/mvp_d/expansion_pain_extraction_report.md").write_text(
        "- selected_for_llm: 3\n- should_extract_true: 0\n- rejected: 3\n- status: completed\n",
        encoding="utf-8",
    )
    (tmp_path / "data/processed/mvp_d").mkdir(parents=True)
    (tmp_path / "data/processed/mvp_d/seeded_query_plan.jsonl").write_text(paths["queries"].read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "data/processed/mvp_d/expansion_evidence_candidates.jsonl").write_text(paths["candidates"].read_text(encoding="utf-8"), encoding="utf-8")

    summary = run_mvp_d2(skip_pilot=True)

    assert summary.engineering_acceptance == "pass"
    assert summary.product_acceptance == "partial"
    assert summary.generated_v2_queries >= 6
    assert (tmp_path / "outputs/mvp_d2/mvp_d2_summary_report.md").exists()
