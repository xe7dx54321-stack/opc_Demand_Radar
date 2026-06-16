from pathlib import Path

from demand_radar.mvp_d.seed_selector import select_seeds


def test_select_seeds_picks_true_pain_needs_more_evidence(tmp_path):
    pain_items = tmp_path / "pain.jsonl"
    reviews = tmp_path / "reviews.jsonl"
    pain_items.write_text(
        "\n".join(
            [
                '{"pain_item_id":"pain__000022","candidate_id":"cand_022","title":"Seed A","source_url":"https://news.ycombinator.com/item?id=1","persona":"VC analyst","workflow_stage":"deal_sourcing","pain_type":"manual_workflow","pain_description_zh":"pain","evidence_quote":"quote","source_type":"community_discussion"}',
                '{"pain_item_id":"pain__000034","candidate_id":"cand_034","title":"Seed B","source_url":"https://news.ycombinator.com/item?id=2","persona":"VC analyst","workflow_stage":"deal_sourcing","pain_type":"manual_workflow","pain_description_zh":"pain","evidence_quote":"quote","source_type":"community_discussion"}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    reviews.write_text(
        "\n".join(
            [
                '{"review_id":"rev_022","pain_item_id":"pain__000022","candidate_id":"cand_022","true_pain":true,"commercial_potential":"medium","evidence_quality":"strong","action_decision":"needs_more_evidence","created_at":"2026-01-01T00:00:00Z"}',
                '{"review_id":"rev_034","pain_item_id":"pain__000034","candidate_id":"cand_034","true_pain":null,"commercial_potential":"unclear","evidence_quality":"weak","action_decision":"needs_more_evidence","created_at":"2026-01-01T00:00:00Z"}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    seeds, summary = select_seeds(
        pain_items_path=pain_items,
        reviews_path=reviews,
        output_path=tmp_path / "seed_profiles.jsonl",
        report_path=tmp_path / "seed_selection_report.md",
        max_seeds_override=5,
    )

    assert len(seeds) == 1
    assert seeds[0].pain_item_id == "pain__000022"
    assert summary.eligible_seeds == 1
    assert summary.excluded_reviews >= 1
    assert (tmp_path / "seed_selection_report.md").exists()

