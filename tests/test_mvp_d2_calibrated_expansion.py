import json

from demand_radar.mvp_d2.calibrated_expansion_runner import run_calibrated_expansion
from tests.test_mvp_d2_fixtures import write_d2_fixture, write_jsonl


def test_calibrated_pilot_blocks_without_search_provider(tmp_path, monkeypatch):
    for key in [
        "TAVILY_API_KEY",
        "SERPAPI_API_KEY",
        "SERP_API_KEY",
        "BING_SEARCH_API_KEY",
        "GOOGLE_SEARCH_API_KEY",
        "BRAVE_SEARCH_API_KEY",
        "DEMAND_RADAR_SEARCH_PROVIDER",
    ]:
        monkeypatch.delenv(key, raising=False)
    paths = write_d2_fixture(tmp_path, count=1)

    _, pains, summary = run_calibrated_expansion(
        query_plan_path=paths["queries"],
        output_candidates_path=tmp_path / "calibrated_candidates.jsonl",
        output_pain_items_path=tmp_path / "calibrated_pain.jsonl",
        report_path=tmp_path / "calibrated_expansion_report.md",
    )

    assert pains == []
    assert summary["status"] == "blocked"
    assert summary["blocked_reason"] == "blocked_by_missing_search_provider"
    assert (tmp_path / "calibrated_expansion_report.md").exists()


def test_calibrated_pilot_with_mock_candidates_runs_gate_and_extraction(tmp_path, monkeypatch):
    import demand_radar.mvp_d.expansion_extraction as extraction_mod

    paths = write_d2_fixture(tmp_path, count=1)
    mock_candidates = tmp_path / "mock_candidates.jsonl"
    write_jsonl(
        mock_candidates,
        [
            {
                "candidate_id": "cal_cand_1",
                "raw_signal_id": "raw_1",
                "source_id": "src",
                "source_type": "community_discussion",
                "source_name": "HN",
                "source_url": "https://news.ycombinator.com/item?id=42",
                "title": "VC analyst spreadsheet pain",
                "raw_text": "VC analysts spend hours manually tracking startups in spreadsheets. " * 20,
                "domain_id": "ai_investment_tracking",
                "domain_title_zh": "投资研究",
                "collection_query": "VC analyst spreadsheet pain",
                "fetched_at": "2026-01-01T00:00:00Z",
                "source_weight": 0.8,
                "validation_status": "valid",
                "validation_reasons": [],
                "detected_signal_types": [],
                "include_in_evidence_pack": True,
                "metadata": {},
            }
        ],
    )

    def fake_run_expansion_extraction(**kwargs):
        pain_path = kwargs["pain_output_path"]
        pain_rows = [
            {
                "pain_item_id": "pain_1",
                "candidate_id": "cal_cand_1",
                "should_extract": True,
                "reject_reason": None,
                "persona": "VC analyst",
                "workflow_stage": "startup_tracking",
                "pain_type": "manual_workflow",
                "pain_description_zh": "分析师手动用表格追踪公司很耗时。",
                "evidence_quote": "VC analysts spend hours manually tracking startups in spreadsheets.",
                "evidence_strength": "strong",
                "confidence": 0.9,
                "source_url": "https://news.ycombinator.com/item?id=42",
                "source_type": "community_discussion",
                "title": "VC analyst spreadsheet pain",
                "prompt_version": "v1",
                "model": "mock",
                "created_at": "2026-01-01T00:00:00Z",
                "metadata": {},
            }
        ]
        pain_path.parent.mkdir(parents=True, exist_ok=True)
        pain_path.write_text(json.dumps(pain_rows[0], ensure_ascii=False) + "\n", encoding="utf-8")
        return [], pain_rows, {
            "status": "completed",
            "blocked_reason": None,
            "real_llm_run": True,
            "provider": "responses_compatible",
            "model": "mock",
            "allowed_by_gate": 1,
            "blocked_by_gate": 0,
            "selected_for_llm": 1,
            "processed": 1,
            "should_extract_true": 1,
            "strong": 1,
            "medium": 0,
            "weak": 0,
            "rejected": 0,
        }

    monkeypatch.setattr(extraction_mod, "run_expansion_extraction", fake_run_expansion_extraction)
    import demand_radar.mvp_d2.calibrated_expansion_runner as runner_mod

    monkeypatch.setattr(runner_mod, "run_expansion_extraction", fake_run_expansion_extraction)
    candidates, pains, summary = run_calibrated_expansion(
        query_plan_path=paths["queries"],
        candidates_path=mock_candidates,
        output_candidates_path=tmp_path / "calibrated_candidates.jsonl",
        output_pain_items_path=tmp_path / "calibrated_pain.jsonl",
        report_path=tmp_path / "calibrated_expansion_report.md",
    )

    assert len(candidates) == 1
    assert len(pains) == 1
    assert summary["should_extract_true"] == 1
    assert summary["yield_rate"] == 1.0
    assert candidates[0]["metadata"]["seed_query_id"] == "query_1"

