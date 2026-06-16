import json
from pathlib import Path

from demand_radar.mvp_d.mvp_d_pipeline import run_mvp_d


def test_mvp_d_pipeline_graceful_no_seeds(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs" / "seeded_expansion_config.yaml").write_text(
        """
seeded_expansion:
  domain_id: ai_investment_tracking
  input:
    extracted_pain_items_path: data/processed/mvp_b/extracted_pain_items.jsonl
    reviews_path: data/processed/mvp_c/pain_signal_reviews.jsonl
  output:
    seed_profiles_path: data/processed/mvp_d/seed_profiles.jsonl
    query_plan_path: data/processed/mvp_d/seeded_query_plan.jsonl
    expansion_evidence_candidates_path: data/processed/mvp_d/expansion_evidence_candidates.jsonl
    expansion_domain_relevance_path: data/processed/mvp_d/expansion_domain_relevance_scores.jsonl
    expansion_pain_items_path: data/processed/mvp_d/expansion_pain_items.jsonl
    seed_consolidation_path: data/processed/mvp_d/seed_evidence_consolidation.jsonl
    consolidated_evidence_path: data/processed/mvp_d/consolidated_evidence_themes.jsonl
""",
        encoding="utf-8",
    )

    summary = run_mvp_d(max_seeds=0, max_queries=0, max_results=0)

    assert summary.engineering_acceptance == "pass"
    assert summary.eligible_seeds == 0
    assert Path("outputs/mvp_d/mvp_d_summary_report.md").exists()

