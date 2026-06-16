import json

from demand_radar.mvp_d.evidence_consolidator import consolidate_evidence


def test_evidence_consolidator_outputs_watch_and_pursue(tmp_path):
    seeds = tmp_path / "seeds.jsonl"
    candidates = tmp_path / "candidates.jsonl"
    pains = tmp_path / "pain.jsonl"
    seeds.write_text(
        "\n".join(
            [
                json.dumps({"seed_id": "seed_1", "pain_item_id": "pain_1", "title": "Seed 1", "true_pain": True, "commercial_potential": "high"}),
                json.dumps({"seed_id": "seed_2", "pain_item_id": "pain_2", "title": "Seed 2", "true_pain": True, "commercial_potential": "medium"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    candidate_rows = [
        {"candidate_id": f"cand_{i}", "source_url": f"https://news.ycombinator.com/item?id={i}", "metadata": {"seed_id": "seed_1"}}
        for i in range(3)
    ] + [
        {"candidate_id": "cand_4", "source_url": "https://news.ycombinator.com/item?id=4", "metadata": {"seed_id": "seed_2"}}
    ]
    candidates.write_text("\n".join(json.dumps(r) for r in candidate_rows) + "\n", encoding="utf-8")
    pain_rows = [
        {"candidate_id": f"cand_{i}", "should_extract": True, "evidence_strength": "strong", "source_url": f"https://news.ycombinator.com/item?id={i}"}
        for i in range(3)
    ] + [
        {"candidate_id": "cand_4", "should_extract": True, "evidence_strength": "weak", "source_url": "https://news.ycombinator.com/item?id=4"}
    ]
    pains.write_text("\n".join(json.dumps(r) for r in pain_rows) + "\n", encoding="utf-8")

    items = consolidate_evidence(
        seeds_path=seeds,
        candidates_path=candidates,
        pain_items_path=pains,
        output_path=tmp_path / "consolidation.jsonl",
        report_path=tmp_path / "report.md",
    )

    recs = {item.seed_id: item.recommendation for item in items}
    assert recs["seed_1"] == "pursue_candidate"
    assert recs["seed_2"] == "watch"
    assert (tmp_path / "report.md").exists()

