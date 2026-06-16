import json

from demand_radar.ui.mvp_d_service import get_mvp_d_overview


def test_mvp_d_ui_service_reads_overview(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data/processed/mvp_d").mkdir(parents=True)
    (tmp_path / "data/processed/mvp_d/seed_profiles.jsonl").write_text(
        '{"seed_id":"seed_1","pain_item_id":"pain_1","title":"Seed 1","source_url":"https://a.com","true_pain":true,"commercial_potential":"high","evidence_quality":"strong","action_decision":"needs_more_evidence","expansion_priority":"high","seed_reason_zh":"ok","created_at":"2026-01-01T00:00:00Z"}\n',
        encoding="utf-8",
    )
    (tmp_path / "data/processed/mvp_d/seeded_query_plan.jsonl").write_text("[]\n", encoding="utf-8")
    (tmp_path / "data/processed/mvp_d/expansion_evidence_candidates.jsonl").write_text("[]\n", encoding="utf-8")
    (tmp_path / "data/processed/mvp_d/expansion_pain_items.jsonl").write_text("[]\n", encoding="utf-8")
    (tmp_path / "data/processed/mvp_d/seed_evidence_consolidation.jsonl").write_text("[]\n", encoding="utf-8")
    (tmp_path / "data/processed/mvp_d/consolidated_evidence_themes.jsonl").write_text("[]\n", encoding="utf-8")
    (tmp_path / "outputs").mkdir()
    (tmp_path / "outputs/run_summary.json").write_text(json.dumps({"engineering_acceptance": "pass"}), encoding="utf-8")

    overview = get_mvp_d_overview()
    assert overview["eligible_seeds"] == 1
    assert overview["engineering_acceptance"] == "pass"

