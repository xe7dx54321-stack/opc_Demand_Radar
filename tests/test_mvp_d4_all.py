"""MVP-D4 tests."""
from __future__ import annotations
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


# ── Foundation adapter ────────────────────────────────────────────────────────

def test_check_foundation_version_ok():
    from demand_radar.mvp_d4.foundation_search_adapter import check_foundation_version
    ok, ver = check_foundation_version()
    # 0.1.2 is installed
    assert ok is True
    assert "0.1" in ver


def test_check_foundation_version_mock_old(monkeypatch):
    import opc_foundation
    monkeypatch.setattr(opc_foundation, "__version__", "0.0.9")
    from demand_radar.mvp_d4 import foundation_search_adapter as fa
    import importlib
    importlib.reload(fa)
    ok, ver = fa.check_foundation_version()
    assert ok is False
    monkeypatch.setattr(opc_foundation, "__version__", "0.1.2")
    importlib.reload(fa)


def test_detect_provider_no_key(monkeypatch):
    for k in ["TAVILY_API_KEY", "BRAVE_SEARCH_API_KEY"]:
        monkeypatch.delenv(k, raising=False)
    from demand_radar.mvp_d4.foundation_search_adapter import detect_provider
    assert detect_provider() is None


def test_detect_provider_with_tavily(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test_key_abc")
    from demand_radar.mvp_d4.foundation_search_adapter import detect_provider
    result = detect_provider()
    assert result == "tavily"


# ── Query selector ────────────────────────────────────────────────────────────

def test_select_queries_from_v2(tmp_path):
    queries = []
    for seed_id in ["seed__000001", "seed__000002"]:
        for i, qt in enumerate(["manual_workflow","pain_phrase","spreadsheet_workaround",
                                 "workaround_phrase","complaint_phrase","buying_intent"]):
            queries.append({
                "query_id": f"q_{seed_id}_{i}", "seed_id": seed_id,
                "pain_item_id": "pain__000022",
                "query": f"test query {i}", "query_type": qt,
                "connector": "hacker_news", "priority": "high",
                "metadata": {"query_version": "v2"},
            })
    v2_path = tmp_path / "calibrated_query_plan_v2.jsonl"
    with v2_path.open("w") as f:
        for q in queries:
            f.write(json.dumps(q) + chr(10))
    out_path = tmp_path / "out.jsonl"
    from demand_radar.mvp_d4.query_selector import select_queries
    selected = select_queries(v2_path=v2_path, output_path=out_path, max_queries=24)
    assert len(selected) > 0
    seed_ids = {q.get("seed_id") for q in selected}
    assert "seed__000001" in seed_ids
    assert "seed__000002" in seed_ids
    # Priority types should come first
    types = [q.get("query_type") for q in selected[:4]]
    assert any(t in types for t in ["manual_workflow", "pain_phrase"])


def test_select_queries_empty_v2(tmp_path):
    from demand_radar.mvp_d4.query_selector import select_queries
    result = select_queries(v2_path=tmp_path / "nope.jsonl")
    assert result == []


# ── Search result mapper ──────────────────────────────────────────────────────

def _make_foundation_result(url, title="Test", snippet="some content"):
    r = MagicMock()
    r.result_id = "sr_x"
    r.provider = "tavily"
    r.query = "investment research manual"
    r.title = title
    r.url = url
    r.snippet = snippet
    r.published_at = None
    r.rank = 1
    r.result_domain = url.split("/")[2] if "//" in url else url
    return r


def test_mapper_basic():
    from demand_radar.mvp_d4.search_result_mapper import map_results
    results = [_make_foundation_result("https://hn.com/1")]
    mapped = map_results(results, query_meta={"query_id": "q1", "seed_id": "s1"})
    assert len(mapped) == 1
    assert mapped[0]["url"] == "https://hn.com/1"
    assert mapped[0]["seed_id"] == "s1"


def test_mapper_dedup():
    from demand_radar.mvp_d4.search_result_mapper import map_results
    r1 = _make_foundation_result("https://hn.com/1")
    r2 = _make_foundation_result("https://hn.com/1")
    r3 = _make_foundation_result("https://hn.com/2")
    mapped = map_results([r1, r2, r3])
    assert len(mapped) == 2


def test_mapper_blocks_example_com():
    from demand_radar.mvp_d4.search_result_mapper import map_results
    r1 = _make_foundation_result("https://example.com/test")
    r2 = _make_foundation_result("https://hn.com/real")
    mapped = map_results([r1, r2])
    urls = [m["url"] for m in mapped]
    assert "https://example.com/test" not in urls
    assert "https://hn.com/real" in urls


# ── Evidence candidate builder ────────────────────────────────────────────────

def test_build_candidates_snippet_only():
    from demand_radar.mvp_d4.evidence_candidate_builder import build_candidates
    mapped = [{
        "result_id": "sr1", "provider": "tavily", "query_id": "q1",
        "seed_id": "s1", "pain_item_id": "p1", "query": "test",
        "query_type": "pain_phrase", "title": "VC Research Pain",
        "url": "https://hn.com/1",
        "snippet": "VC analysts spend 3 hours manually researching each deal",
        "rank": 1, "result_domain": "hn.com",
    }]
    candidates = build_candidates(mapped, use_foundation_extraction=False)
    assert len(candidates) == 1
    c = candidates[0]
    assert c.source_url == "https://hn.com/1"
    assert (c.metadata or {}).get("raw_text_source") == "snippet_only"
    assert (c.metadata or {}).get("foundation_search") is True


def test_build_candidates_full_page_mock(monkeypatch):
    from demand_radar.mvp_d4.evidence_candidate_builder import build_candidates
    mock_result = MagicMock()
    mock_result.success = True
    mock_result.text = "VC analysts complain about manual research workflows " * 30
    monkeypatch.setattr(
        "demand_radar.mvp_d4.foundation_search_adapter.extract_page_foundation",
        lambda url, timeout=10: mock_result,
    )
    mapped = [{
        "result_id": "sr2", "provider": "tavily", "query_id": "q2",
        "seed_id": "s1", "pain_item_id": "p1", "query": "test",
        "query_type": "manual_workflow", "title": "Research Pain",
        "url": "https://hn.com/2", "snippet": "short",
        "rank": 1, "result_domain": "hn.com",
    }]
    candidates = build_candidates(mapped, use_foundation_extraction=True)
    assert len(candidates) == 1
    meta = candidates[0].metadata or {}
    assert meta.get("raw_text_source") == "full_page"


# ── Gate integration ──────────────────────────────────────────────────────────

def test_gate_blocks_example_domain():
    from demand_radar.mvp_d.real_signal_gate import run_gate
    cands = [
        {"candidate_id": "c1", "source_url": "https://example.com/page",
         "raw_text": "x" * 200, "title": "T1", "metadata": {"foundation_search": True}},
        {"candidate_id": "c2", "source_url": "https://hn.com/real",
         "raw_text": "investment research pain point " * 10, "title": "T2",
         "metadata": {"foundation_search": True}},
    ]
    allowed, blocked = run_gate(cands)
    assert any(r.candidate_id == "c2" for r in allowed)
    assert any(r.candidate_id == "c1" for r in blocked)


# ── Yield analyzer ────────────────────────────────────────────────────────────

def test_yield_analyzer_zero():
    from demand_radar.mvp_d4.yield_analyzer import analyze_yield
    m = analyze_yield([], [], [], [])
    assert m["yield_rate"] == 0.0


def test_yield_analyzer_with_pain(tmp_path):
    from demand_radar.mvp_d4.yield_analyzer import analyze_yield
    pain_items = []
    for strong in [True, True, False]:
        m = MagicMock()
        m.should_extract = strong
        m.evidence_strength = "strong" if strong else "reject"
        m.metadata = {}
        pain_items.append(m)
    mapped = [{"url": "https://hn.com/1", "query_type": "pain_phrase",
               "seed_id": "s1", "result_domain": "hn.com"}]
    gate_allowed = [MagicMock(metadata={"raw_text_source": "full_page"})]
    result = analyze_yield(
        ["q1"], mapped, gate_allowed, pain_items,
        output_path=tmp_path / "yield.md",
    )
    assert result["should_extract_true"] == 2
    assert result["selected_for_llm"] == 3
    assert abs(result["yield_rate"] - 2/3) < 0.01


# ── Pipeline (blocked) ────────────────────────────────────────────────────────

def test_pipeline_blocked_no_provider(monkeypatch, tmp_path):
    for k in ["TAVILY_API_KEY", "BRAVE_SEARCH_API_KEY"]:
        monkeypatch.delenv(k, raising=False)
    from demand_radar.mvp_d4.foundation_search_pipeline import run_mvp_d4
    result = run_mvp_d4()
    assert result.blocked_reason == "blocked_by_missing_search_provider"
    assert result.gate_allowed == 0
    assert result.should_extract_true == 0


# ── Reports ───────────────────────────────────────────────────────────────────

def test_build_gate_report(tmp_path):
    from demand_radar.mvp_d4.mvp_d4_report import build_gate_report
    allowed = [MagicMock(block_reason=None, metadata={"raw_text_source": "full_page"})]
    blocked = [MagicMock(block_reason="blocked_domain:example.com")]
    report = build_gate_report(allowed, blocked, output_path=tmp_path / "gate.md")
    assert "total_candidates: 2" in report
    assert "allowed: 1" in report


def test_build_summary_report_blocked(tmp_path):
    from demand_radar.mvp_d4.mvp_d4_report import build_summary_report
    pilot = {
        "status": "blocked", "blocked_reason": "blocked_by_missing_search_provider",
        "provider": "none", "model": "none", "real_llm_run": False,
        "selected_queries": 0, "total_search_results": 0, "unique_urls": 0,
        "evidence_candidates": 0, "gate_allowed": 0, "gate_blocked": 0,
        "snippet_only_count": 0, "full_page_count": 0,
        "selected_for_llm": 0, "should_extract_true": 0,
        "strong": 0, "medium": 0, "weak": 0, "failures": 0,
        "errors": [], "pain_items": [],
    }
    out = tmp_path / "summary.md"
    report = build_summary_report(pilot, output_path=out)
    assert "blocked_by_missing_search_provider" in report
    assert out.exists()


# ── CLI tests ─────────────────────────────────────────────────────────────────

def test_cli_detect_foundation_search_provider_no_key(monkeypatch):
    for k in ["TAVILY_API_KEY", "BRAVE_SEARCH_API_KEY"]:
        monkeypatch.delenv(k, raising=False)
    from typer.testing import CliRunner
    from demand_radar.cli import app
    runner = CliRunner()
    result = runner.invoke(app, ["detect-foundation-search-provider"])
    assert result.exit_code == 0
    assert "none" in result.output.lower() or "0.1.2" in result.output


def test_cli_run_mvp_d4_no_provider(monkeypatch):
    for k in ["TAVILY_API_KEY", "BRAVE_SEARCH_API_KEY"]:
        monkeypatch.delenv(k, raising=False)
    from typer.testing import CliRunner
    from demand_radar.cli import app
    runner = CliRunner()
    result = runner.invoke(app, ["run-mvp-d4", "--domain", "ai_investment_tracking", "--fake-llm"])
    assert result.exit_code == 0
    assert "blocked" in result.output.lower() or "provider" in result.output.lower()
