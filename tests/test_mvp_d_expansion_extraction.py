import json

from demand_radar.mvp_d.expansion_extraction import run_expansion_extraction
from demand_radar.semantic_merge.llm_client import FakeLLMClient


class _FailingLLM:
    provider = "fake"
    model = "fake"

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        raise RuntimeError("no llm")


def _write_cfg(path):
    path.write_text(
        """
seeded_expansion:
  output:
    expansion_evidence_candidates_path: candidates.jsonl
    expansion_domain_relevance_path: rel.jsonl
    expansion_pain_items_path: pain.jsonl
  gates:
    require_raw_text_min_chars: 20
  llm:
    enabled: true
    default_provider: responses_compatible
    default_model: claude-sonnet-4-6
    temperature: 0
    max_tokens: 4000
    cache_enabled: true
    run_scope: demand_radar_mvp_d_seeded_expansion
    prompt_version: acquired_signal_pain_extraction_v1
""",
        encoding="utf-8",
    )


def _candidate(candidate_id="cand_1", seed_id="seed_1", text=None):
    quote = "We spend hours manually tracking AI startups in spreadsheets."
    return {
        "candidate_id": candidate_id,
        "source_url": f"https://news.ycombinator.com/item?id={candidate_id}",
        "title": "Real investment workflow pain",
        "raw_text": text or (quote + " " + "AI investment research workflow " * 10),
        "source_type": "community_discussion",
        "metadata": {"seed_id": seed_id, "seed_query_id": "query_1", "pain_item_id": "pain_seed"},
    }


def _llm_response():
    return json.dumps(
        {
            "candidate_id": "cand_1",
            "should_extract": True,
            "reject_reason": None,
            "persona": "VC analyst",
            "persona_confidence": 0.86,
            "workflow_stage": "startup_tracking",
            "job_to_be_done": "Track AI startups efficiently",
            "pain_type": "manual_workflow",
            "pain_description_zh": "投资分析师手动追踪 AI 创业公司非常耗时。",
            "evidence_quote": "We spend hours manually tracking AI startups in spreadsheets.",
            "current_solution": "spreadsheets",
            "paid_alternative": None,
            "business_impact": "hours wasted",
            "time_cost_signal": "hours",
            "budget_signal": None,
            "commercial_signal_type": "manual_labor_cost",
            "evidence_strength": "strong",
            "confidence": 0.84,
            "reasoning_summary_zh": "原文明确表达了手工追踪工作流的时间成本。",
        },
        ensure_ascii=False,
    )


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
        llm_pass_report_path=tmp_path / "llm_pass.md",
        llm_client=_FailingLLM(),
    )

    assert summary["blocked_by_gate"] >= 1
    assert summary["selected_for_llm"] <= summary["allowed_by_gate"]
    assert (tmp_path / "gate.md").exists()
    assert (tmp_path / "report.md").exists()


def test_expansion_extraction_with_llm_sets_real_run_and_seed_metadata(tmp_path, monkeypatch):
    import demand_radar.mvp_d.expansion_extraction as mod

    cfg = tmp_path / "config.yaml"
    _write_cfg(cfg)
    candidates = tmp_path / "candidates.jsonl"
    candidates.write_text(json.dumps(_candidate(), ensure_ascii=False) + "\n", encoding="utf-8")

    class _Rel:
        def model_dump(self):
            return {"candidate_id": "cand_1", "relevance_decision": "include", "relevance_score": 0.9}

        def model_dump_json(self):
            return json.dumps(self.model_dump(), ensure_ascii=False)

    monkeypatch.setattr(mod, "run_domain_relevance_filter", lambda items, **kwargs: [_Rel()])
    llm = FakeLLMClient(default=_llm_response())
    llm.model = "claude-sonnet-4-6"
    llm.provider = "responses_compatible"

    _, pain_rows, summary = run_expansion_extraction(
        config_path=cfg,
        candidates_path=candidates,
        relevance_output_path=tmp_path / "rel.jsonl",
        pain_output_path=tmp_path / "pain.jsonl",
        gate_report_path=tmp_path / "gate.md",
        report_path=tmp_path / "report.md",
        llm_pass_report_path=tmp_path / "llm_pass.md",
        llm_client=llm,
        use_cache=False,
    )

    assert summary["real_llm_run"] is True
    assert summary["provider"] == "responses_compatible"
    assert summary["model"] == "claude-sonnet-4-6"
    assert summary["selected_for_llm"] == 1
    assert summary["should_extract_true"] == 1
    assert pain_rows[0]["metadata"]["seed_id"] == "seed_1"
    assert pain_rows[0]["metadata"]["real_llm_run"] is True
    assert pain_rows[0]["source_url"].startswith("https://news.ycombinator.com")
    assert "real_llm_run: true" in (tmp_path / "report.md").read_text(encoding="utf-8")


def test_expansion_extraction_blocks_when_llm_config_missing(tmp_path, monkeypatch):
    for key in [
        "DEMAND_RADAR_LLM_BASE_URL",
        "DEMAND_RADAR_LLM_API_KEY",
        "DEMAND_RADAR_LLM_MODEL",
        "DEMAND_RADAR_LLM_PROVIDER",
        "LLM_PROVIDER",
        "LLM_MODEL",
        "LLM_API_KEY",
        "LLM_BASE_URL",
    ]:
        monkeypatch.delenv(key, raising=False)
    cfg = tmp_path / "config.yaml"
    _write_cfg(cfg)
    candidates = tmp_path / "candidates.jsonl"
    candidates.write_text(json.dumps(_candidate(), ensure_ascii=False) + "\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    _, pain_rows, summary = run_expansion_extraction(
        config_path=cfg,
        candidates_path=candidates,
        relevance_output_path=tmp_path / "rel.jsonl",
        pain_output_path=tmp_path / "pain.jsonl",
        gate_report_path=tmp_path / "gate.md",
        report_path=tmp_path / "report.md",
        llm_pass_report_path=tmp_path / "llm_pass.md",
        use_cache=True,
    )

    assert pain_rows == []
    assert summary["status"] == "blocked"
    assert summary["real_llm_run"] is False
    assert summary["selected_for_llm"] == 1
    assert "missing_llm_config" in summary["blocked_reason"]


def test_mvp_d_cache_requires_matching_provenance(tmp_path):
    from demand_radar.mvp_d.llm_cache import MVPDPainExtractionCache, raw_text_hash

    cache = MVPDPainExtractionCache(path=tmp_path / "cache.jsonl", enabled=True)
    raw_hash = raw_text_hash("same raw")
    cache.set(
        candidate_id="cand_1",
        provider="responses_compatible",
        model="claude-sonnet-4-6",
        prompt_version="v1",
        run_scope="scope_a",
        raw_hash=raw_hash,
        result={"should_extract": True},
    )
    assert cache.get(
        candidate_id="cand_1",
        provider="responses_compatible",
        model="claude-sonnet-4-6",
        prompt_version="v1",
        run_scope="scope_a",
        raw_hash=raw_hash,
    ) == {"should_extract": True}
    assert cache.get(
        candidate_id="cand_1",
        provider="responses_compatible",
        model="other-model",
        prompt_version="v1",
        run_scope="scope_a",
        raw_hash=raw_hash,
    ) is None
    assert cache.stats.stale_prevented == 1
