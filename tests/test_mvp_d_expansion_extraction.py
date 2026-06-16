import json

from demand_radar.mvp_d.expansion_extraction import run_expansion_extraction


class _FailingLLM:
    provider = "fake"
    model = "fake"

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        raise RuntimeError("no llm")


def test_expansion_extraction_blocks_example_and_short_text(tmp_path, monkeypatch):
    candidates = tmp_path / "candidates.jsonl"
    long_text = "x" * 200
    candidates.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "candidate_id": "cand_1",
                        "source_url": "https://example.com/item/1",
                        "title": "Example Domain",
                        "raw_text": long_text,
                        "source_type": "community_discussion",
                        "metadata": {"seed_id": "seed_1", "seed_query_id": "query_1"},
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "candidate_id": "cand_2",
                        "source_url": "https://news.ycombinator.com/item?id=1",
                        "title": "Real item",
                        "raw_text": "too short",
                        "source_type": "community_discussion",
                        "metadata": {"seed_id": "seed_1", "seed_query_id": "query_1"},
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    import demand_radar.mvp_d.expansion_extraction as mod

    def fake_domain_relevance_filter(items, **kwargs):
        return [
            type("R", (), {"model_dump": lambda self=None, i=item: {"candidate_id": i["candidate_id"], "relevance_decision": "include", "relevance_score": 0.9}})()
            for item in items
        ]

    monkeypatch.setattr(mod, "run_domain_relevance_filter", lambda items, **kwargs: [
        type("R", (), {"model_dump": lambda self=None, cid=item["candidate_id"]: {"candidate_id": cid, "relevance_decision": "include", "relevance_score": 0.9}})()
        for item in items
    ])

    relevance_rows, pain_rows, summary = run_expansion_extraction(
        candidates_path=candidates,
        relevance_output_path=tmp_path / "rel.jsonl",
        pain_output_path=tmp_path / "pain.jsonl",
        gate_report_path=tmp_path / "gate.md",
        report_path=tmp_path / "report.md",
        llm_client=_FailingLLM(),
    )

    assert summary["blocked_by_gate"] >= 1
    assert summary["selected_for_llm"] <= summary["allowed_by_gate"]
    assert (tmp_path / "gate.md").exists()
    assert (tmp_path / "report.md").exists()
