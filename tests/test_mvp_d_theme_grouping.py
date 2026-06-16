import json

from demand_radar.mvp_d.theme_grouping import build_demand_themes


def test_theme_grouping_by_persona_workflow_pain(tmp_path):
    seeds = tmp_path / "seeds.jsonl"
    consolidations = tmp_path / "consolidations.jsonl"
    seeds.write_text(
        "\n".join(
            [
                json.dumps({"seed_id": "seed_1", "pain_item_id": "pain_1", "persona": "VC analyst", "workflow_stage": "deal_sourcing", "pain_type": "manual_workflow", "true_pain": True, "commercial_potential": "high", "source_url": "https://a.com/1"}),
                json.dumps({"seed_id": "seed_2", "pain_item_id": "pain_2", "persona": "VC analyst", "workflow_stage": "deal_sourcing", "pain_type": "manual_workflow", "true_pain": True, "commercial_potential": "medium", "source_url": "https://a.com/2"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    consolidations.write_text(
        "\n".join(
            [
                json.dumps({"seed_id": "seed_1", "pain_item_id": "pain_1", "recommendation": "watch", "new_extracted_pain_count": 1, "recommendation_reason_zh": "有证据"}),
                json.dumps({"seed_id": "seed_2", "pain_item_id": "pain_2", "recommendation": "needs_more_evidence", "new_extracted_pain_count": 0, "recommendation_reason_zh": "需要更多证据"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    themes = build_demand_themes(seeds, consolidations, tmp_path / "themes.jsonl", tmp_path / "report.md")

    assert len(themes) == 1
    assert themes[0].reviewed_seed_count == 2
    assert themes[0].action_recommendation == "watch"
    assert (tmp_path / "report.md").exists()

