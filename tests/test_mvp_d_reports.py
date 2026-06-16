from demand_radar.mvp_d.mvp_d_report import build_mvp_d_summary_report
from demand_radar.mvp_d.seed_schema import MVPDRunSummary


def test_mvp_d_summary_report_generates(tmp_path):
    summary = MVPDRunSummary(
        domain_id="ai_investment_tracking",
        generated_at="2026-01-01T00:00:00Z",
        total_reviews=5,
        eligible_seeds=4,
        total_queries=20,
        engineering_acceptance="pass",
        product_acceptance="partial",
        can_enter_second_review=True,
        can_enter_product_discovery=False,
        reason="insufficient expansion evidence",
    )
    out = build_mvp_d_summary_report(summary, report_path=tmp_path / "summary.md")
    assert out.exists()
    assert "MVP-D Seeded Evidence Expansion Summary" in out.read_text(encoding="utf-8")

