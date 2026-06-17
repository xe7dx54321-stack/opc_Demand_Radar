from demand_radar.mvp_d2.reject_diagnostics_runner import (
    bucket_raw_text,
    map_reject_category,
    run_reject_diagnostics,
)
from tests.test_mvp_d2_fixtures import write_d2_fixture


def test_rejected_candidates_can_be_diagnosed(tmp_path):
    paths = write_d2_fixture(tmp_path, count=28)
    diagnostics, summary = run_reject_diagnostics(
        candidates_path=paths["candidates"],
        pain_items_path=paths["pain_items"],
        seed_profiles_path=paths["seeds"],
        query_plan_path=paths["queries"],
        output_path=tmp_path / "reject_diagnostics.jsonl",
        report_path=tmp_path / "reject_diagnostics_report.md",
    )

    assert len(diagnostics) == 28
    assert summary["total_rejected"] == 28
    assert diagnostics[0].seed_id == "seed_1"
    assert diagnostics[0].query
    assert diagnostics[0].reject_category in {"technical_issue_not_business_pain", "generic_article", "domain_out"}
    assert (tmp_path / "reject_diagnostics_report.md").exists()


def test_reject_reason_maps_to_categories():
    assert bucket_raw_text(100) == "too_thin"
    assert bucket_raw_text(500) == "adequate"
    assert bucket_raw_text(2000) == "rich"
    assert map_reject_category(
        "domain relevance excluded or score too low (0.05)",
        candidate={
            "source_type": "github_issue",
            "title": "Runtime API bug",
            "raw_text": "worker runtime schema API build implementation bug " * 50,
        },
        raw_text_quality="rich",
    ) == "technical_issue_not_business_pain"
    assert map_reject_category("quote missing", raw_text_quality="adequate") == "no_evidence_quote"

