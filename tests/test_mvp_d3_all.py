"""Tests for MVP-D3 search provider pilot."""
from __future__ import annotations
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from demand_radar.mvp_d3.search_provider_schema import (
    SearchResultItem, SearchQuerySelection, MVP_D3_RunSummary,
)
from demand_radar.mvp_d3.search_query_selector import select_queries
from demand_radar.mvp_d3._impl import normalize_results, build_candidates, analyze_yield


# ── Schema tests ──────────────────────────────────────────────────────────────

def test_search_result_item_valid():
    r = SearchResultItem(
        result_id="sr_001", provider="tavily",
        query_id="q_001", seed_id="seed__000001",
        query="investment research manual", query_type="manual_workflow",
        title="VC Research Pain", url="https://news.ycombinator.com/item?id=123",
        snippet="analysts spend 3 hours manually", rank=1, created_at="2026-06-17T00:00:00Z",
    )
    assert r.provider == "tavily"
    assert r.url == "https://news.ycombinator.com/item?id=123"


def test_mvp_d3_run_summary_defaults():
    s = MVP_D3_RunSummary(generated_at="2026-06-17T00:00:00Z")
    assert s.provider == "none"
    assert s.blocked_reason is None


# ── Provider detection ────────────────────────────────────────────────────────

def test_detect_provider_no_key(monkeypatch):
    for k in ["TAVILY_API_KEY","BRAVE_SEARCH_API_KEY","SERPAPI_API_KEY","BING_SEARCH_API_KEY","GOOGLE_CSE_API_KEY"]:
        monkeypatch.delenv(k, raising=False)
    from demand_radar.mvp_d3.search_provider_client import detect_provider
    provider, key = detect_provider()
    assert provider is None
    assert key is None


def test_detect_provider_tavily(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test_key_123")
    from demand_radar.mvp_d3.search_provider_client import detect_provider
    provider, key = detect_provider()
    assert provider == "tavily"
    assert key == "test_key_123"


def test_make_search_client_returns_none_without_key(monkeypatch):
    for k in ["TAVILY_API_KEY","BRAVE_SEARCH_API_KEY","SERPAPI_API_KEY","BING_SEARCH_API_KEY","GOOGLE_CSE_API_KEY"]:
        monkeypatch.delenv(k, raising=False)
    from demand_radar.mvp_d3.search_provider_client import make_search_client
    client = make_search_client()
    assert client is None


# ── Query selector ────────────────────────────────────────────────────────────

def test_select_queries_from_v2(tmp_path):
    # Create mock v2 query plan
    queries = []
    for seed_id in ["seed__000001", "seed__000002"]:
        for i, qt in enumerate(["manual_workflow","pain_phrase","spreadsheet_workaround",
                                 "workaround_phrase","complaint_phrase","buying_intent","extra"]):
            queries.append({
                "query_id": f"q_{seed_id}_{i}",
                "seed_id": seed_id,
                "pain_item_id": "pain__000022",
                "query": f"test query {i}",
                "query_type": qt,
                "connector": "hacker_news",
                "priority": "high",
                "metadata": {"query_version": "v2"},
            })
    v2_path = tmp_path / "calibrated_query_plan_v2.jsonl"
    with v2_path.open("w") as f:
        for q in queries:
            f.write(json.dumps(q) + "\n")

    out_path = tmp_path / "selected.jsonl"
    selected = select_queries(v2_path=v2_path, output_path=out_path, max_queries=24, max_per_seed=6)
    assert len(selected) > 0
    assert len(selected) <= 24
    # Each seed should have queries
    seed_ids = {s.seed_id for s in selected}
    assert "seed__000001" in seed_ids
    assert "seed__000002" in seed_ids
    # Priority types should come first
    types = [s.query_type for s in selected[:4]]
    assert "manual_workflow" in types or "pain_phrase" in types


def test_select_queries_no_v2(tmp_path):
    selected = select_queries(v2_path=tmp_path / "nonexistent.jsonl")
    assert selected == []


# ── Normalizer ────────────────────────────────────────────────────────────────

def _make_result(url: str, seed_id: str = "seed__000001") -> SearchResultItem:
    return SearchResultItem(
        result_id="sr_x", provider="tavily", query_id="q_x", seed_id=seed_id,
        query="test", query_type="manual_workflow",
        title="Test", url=url, snippet="some content here", rank=1,
        created_at="2026-06-17T00:00:00Z",
    )


def test_normalizer_dedup():
    r1 = _make_result("https://hn.com/1")
    r2 = _make_result("https://hn.com/1")  # duplicate
    r3 = _make_result("https://hn.com/2")
    normalized = normalize_results([r1, r2, r3])
    assert len(normalized) == 2
    assert normalized[0].url == "https://hn.com/1"
    assert normalized[1].url == "https://hn.com/2"


def test_normalizer_blocks_example_com():
    r1 = _make_result("https://example.com/test")
    r2 = _make_result("https://hn.com/real")
    normalized = normalize_results([r1, r2])
    urls = [r.url for r in normalized]
    assert "https://example.com/test" not in urls
    assert "https://hn.com/real" in urls


def test_normalizer_blocks_empty_url():
    r1 = _make_result("")
    normalized = normalize_results([r1])
    assert len(normalized) == 0


# ── Evidence builder ──────────────────────────────────────────────────────────

def test_build_candidates_snippet_only():
    r = _make_result("https://hn.com/1")
    r.snippet = "analysts manually track VC portfolio companies using spreadsheets"
    candidates = build_candidates([r], fetch_pages=False)
    assert len(candidates) == 1
    c = candidates[0]
    assert c.source_url == "https://hn.com/1"
    assert (c.metadata or {}).get("raw_text_source") == "snippet_only"
    assert c.raw_text == r.snippet


def test_build_candidates_seed_metadata():
    r = _make_result("https://hn.com/2")
    r.snippet = "VC analysts spend hours manually gathering data"
    r.query_id = "q_123"
    r.seed_id = "seed__000001"
    r.query_type = "pain_phrase"
    candidates = build_candidates([r], fetch_pages=False)
    meta = candidates[0].metadata or {}
    assert meta.get("seed_id") == "seed__000001"
    assert meta.get("query_type") == "pain_phrase"
    assert meta.get("raw_text_source") == "snippet_only"


# ── Yield analyzer ────────────────────────────────────────────────────────────

def test_analyze_yield_zero():
    result = analyze_yield([], [], [], [])
    assert result["yield_rate"] == 0.0


def test_analyze_yield_with_extractions():
    pain_items = []
    for strong in [True, True, False]:
        m = MagicMock()
        m.should_extract = strong
        m.evidence_strength = "strong" if strong else "reject"
        pain_items.append(m)

    results_mock = [MagicMock(query_type="pain_phrase", seed_id="seed__000001")] * 5
    result = analyze_yield(["q1","q2"], results_mock, ["a","b","c"], pain_items)
    assert result["should_extract_true"] == 2
    assert result["selected_for_llm"] == 3
    assert abs(result["yield_rate"] - 2/3) < 0.01


# ── Pilot runner (blocked) ────────────────────────────────────────────────────

def test_pilot_blocked_no_provider(monkeypatch, tmp_path):
    for k in ["TAVILY_API_KEY","BRAVE_SEARCH_API_KEY","SERPAPI_API_KEY","BING_SEARCH_API_KEY","GOOGLE_CSE_API_KEY"]:
        monkeypatch.delenv(k, raising=False)
    from demand_radar.mvp_d3.search_pilot_runner import run_search_pilot
    result = run_search_pilot(output_dir=tmp_path)
    assert result["status"] == "blocked"
    assert result["blocked_reason"] == "blocked_by_missing_search_provider"
    assert result["gate_allowed"] == 0
    assert result["should_extract_true"] == 0


# ── Pipeline summary ──────────────────────────────────────────────────────────

def test_build_summary_report_blocked(tmp_path):
    from demand_radar.mvp_d3._impl import build_summary_report
    result = {
        "status": "blocked", "blocked_reason": "blocked_by_missing_search_provider",
        "provider": "none", "model": "none", "real_llm_run": False,
        "selected_queries": 0, "total_search_results": 0, "unique_urls": 0,
        "evidence_candidates": 0, "gate_allowed": 0, "gate_blocked": 0,
        "snippet_only_count": 0, "full_page_count": 0,
        "selected_for_llm": 0, "should_extract_true": 0,
        "strong": 0, "medium": 0, "weak": 0, "failures": 0, "errors": [],
        "pain_items": [],
    }
    out = tmp_path / "mvp_d3_summary_report.md"
    report = build_summary_report(result, output_path=out)
    assert "blocked_by_missing_search_provider" in report
    assert out.exists()


# ── Gate integration ─────────────────────────────────────────────────────────

def test_gate_blocks_example_domain():
    from demand_radar.mvp_d.real_signal_gate import run_gate
    cands = [
        {"candidate_id": "c1", "source_url": "https://example.com/test",
         "raw_text": "x" * 200, "title": "Test", "metadata": {}},
        {"candidate_id": "c2", "source_url": "https://hn.com/real",
         "raw_text": "investment research pain " * 10, "title": "Real", "metadata": {}},
    ]
    allowed, blocked = run_gate(cands)
    allowed_ids = {r.candidate_id for r in allowed}
    blocked_ids = {r.candidate_id for r in blocked}
    assert "c1" in blocked_ids
    assert "c2" in allowed_ids


def test_gate_blocks_missing_url():
    from demand_radar.mvp_d.real_signal_gate import run_gate
    cands = [{"candidate_id": "c1", "source_url": "", "raw_text": "x"*200, "title": "T", "metadata": {}}]
    allowed, blocked = run_gate(cands)
    assert len(blocked) == 1


# ── CLI tests ─────────────────────────────────────────────────────────────────

def test_cli_detect_search_provider_no_key(monkeypatch):
    for k in ["TAVILY_API_KEY","BRAVE_SEARCH_API_KEY","SERPAPI_API_KEY","BING_SEARCH_API_KEY","GOOGLE_CSE_API_KEY"]:
        monkeypatch.delenv(k, raising=False)
    from typer.testing import CliRunner
    from demand_radar.cli import app
    runner = CliRunner()
    result = runner.invoke(app, ["detect-search-provider"])
    assert result.exit_code == 0
    assert "blocked" in result.output.lower() or "not" in result.output.lower()


def test_cli_run_mvp_d3_no_provider(monkeypatch, tmp_path):
    for k in ["TAVILY_API_KEY","BRAVE_SEARCH_API_KEY","SERPAPI_API_KEY","BING_SEARCH_API_KEY","GOOGLE_CSE_API_KEY"]:
        monkeypatch.delenv(k, raising=False)
    from typer.testing import CliRunner
    from demand_radar.cli import app
    runner = CliRunner()
    result = runner.invoke(app, ["run-mvp-d3", "--domain", "ai_investment_tracking", "--fake-llm"])
    assert result.exit_code == 0
    assert "blocked" in result.output.lower() or "provider" in result.output.lower()
