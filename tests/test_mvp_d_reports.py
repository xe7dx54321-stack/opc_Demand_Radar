from demand_radar.mvp_d.mvp_d_report import build_mvp_d_summary_report
from demand_radar.mvp_d.seed_schema import MVPDRunSummary
from demand_radar.mvp_d.mvp_d_report import build_mvp_d_llm_expansion_pass_report


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


def test_mvp_d_llm_expansion_pass_report_generates(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data/processed/mvp_d").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data/processed/mvp_d/seed_profiles.jsonl").write_text(
        '{"seed_id":"seed_1","pain_item_id":"pain_1","title":"Seed","source_url":"https://a.com","true_pain":true,"commercial_potential":"high","persona":"VC analyst","workflow_stage":"deal_sourcing","pain_type":"manual_workflow","pain_description_zh":"痛点"}\n',
        encoding="utf-8",
    )
    (tmp_path / "data/processed/mvp_d/seed_evidence_consolidation.jsonl").write_text(
        '{"seed_id":"seed_1","pain_item_id":"pain_1","recommendation":"watch","new_extracted_pain_count":1,"strong_evidence_count":1,"medium_evidence_count":0,"weak_evidence_count":0,"commercial_signal_count":0,"source_url_count":1,"recommendation_reason_zh":"有证据","created_at":"2026-01-01T00:00:00Z"}\n',
        encoding="utf-8",
    )
    (tmp_path / "data/processed/mvp_d/expansion_evidence_candidates.jsonl").write_text(
        '{"candidate_id":"cand_1","source_type":"github_issue","metadata":{"seed_id":"seed_1"}}\n',
        encoding="utf-8",
    )
    (tmp_path / "data/processed/mvp_d/expansion_pain_items.jsonl").write_text(
        '{"candidate_id":"cand_1","should_extract":true,"evidence_strength":"strong","evidence_quote":"quote","persona":"VC analyst","workflow_stage":"deal_sourcing","pain_type":"manual_workflow","commercial_signal_type":"manual_labor_cost","metadata":{"seed_id":"seed_1","cache_hit":false,"quote_matched":true}}\n',
        encoding="utf-8",
    )

    out = build_mvp_d_llm_expansion_pass_report(
        extraction_summary={
            "generated_at": "2026-01-01T00:00:00Z",
            "radar_commit": "abc123",
            "foundation_commit": "unknown",
            "provider": "responses_compatible",
            "model": "claude-sonnet-4-6",
            "real_llm_run": True,
            "cache_enabled": True,
            "prompt_version": "acquired_signal_pain_extraction_v1",
            "run_scope": "demand_radar_mvp_d_seeded_expansion",
            "status": "completed",
            "blocked_reason": None,
            "selected_for_llm": 1,
            "processed": 1,
            "should_extract_true": 1,
            "strong": 1,
            "medium": 0,
            "weak": 0,
            "failures": 0,
            "cache_hits": 0,
        }
    )
    content = out.read_text(encoding="utf-8")
    assert "MVP-D LLM Expansion Pass Report" in content
    assert "real_llm_run: true" in content
    assert "seed_1" in content
