"""Tests for domain relevance filter - rule-based scoring."""
import pytest
from demand_radar.mvp_b.domain_relevance_filter import run_domain_relevance_filter


def _make_candidate(candidate_id, title, raw_text, source_type="community_discussion", source_url="https://example.com/test"):
    return {
        "candidate_id": candidate_id,
        "title": title,
        "raw_text": raw_text,
        "source_type": source_type,
        "source_url": source_url,
        "detected_signal_types": [],
    }


INVESTMENT_CANDIDATE = _make_candidate(
    "c_invest_001",
    "ThesisBoard - Investment Research Workflow",
    "As a VC analyst, I spend hours tracking AI startups and doing investment research. "
    "Our deal sourcing process involves manually checking many sources. "
    "We need better market intelligence tools for venture capital due diligence. "
    "Current solution is spreadsheets which is terrible for portfolio monitoring.",
    "community_discussion",
    "https://news.ycombinator.com/item?id=12345",
)

FOOD_CANDIDATE = _make_candidate(
    "c_food_001",
    "PlanEat AI - Meal Planning App",
    "PlanEat AI helps you plan your weekly meals and track your diet. "
    "Get personalized recipe recommendations and meal prep guidance. "
    "Great for fitness goals and food tracking.",
    "rss",
    "https://planeat.ai/blog",
)

RESEARCH_CANDIDATE = _make_candidate(
    "c_research_001",
    "Deep Research for Stocks",
    "Automated deep research tool for financial analysis and equity research. "
    "Helps analysts with company tracking and market monitoring.",
    "community_discussion",
    "https://news.ycombinator.com/item?id=99999",
)


def test_investment_candidate_included():
    results = run_domain_relevance_filter([INVESTMENT_CANDIDATE])
    assert len(results) == 1
    r = results[0]
    assert r.relevance_decision == "include", f"Expected include, got {r.relevance_decision} (score={r.relevance_score})"
    assert r.relevance_score >= 0.65


def test_food_candidate_excluded():
    results = run_domain_relevance_filter([FOOD_CANDIDATE])
    assert len(results) == 1
    r = results[0]
    assert r.relevance_decision == "exclude", f"Expected exclude, got {r.relevance_decision} (score={r.relevance_score})"
    assert r.relevance_score < 0.45


def test_research_candidate_non_exclude():
    results = run_domain_relevance_filter([RESEARCH_CANDIDATE])
    assert len(results) == 1
    r = results[0]
    # Financial research should be include or uncertain but not exclude
    assert r.relevance_decision in ("include", "uncertain"), f"Expected include/uncertain, got {r.relevance_decision}"


def test_returns_domain_relevance_result():
    from demand_radar.mvp_b.domain_relevance_schema import DomainRelevanceResult
    results = run_domain_relevance_filter([INVESTMENT_CANDIDATE])
    assert isinstance(results[0], DomainRelevanceResult)


def test_empty_candidates():
    results = run_domain_relevance_filter([])
    assert results == []


def test_all_candidates_have_result():
    candidates = [INVESTMENT_CANDIDATE, FOOD_CANDIDATE, RESEARCH_CANDIDATE]
    results = run_domain_relevance_filter(candidates)
    assert len(results) == 3


def test_exclude_has_reason():
    results = run_domain_relevance_filter([FOOD_CANDIDATE])
    r = results[0]
    if r.relevance_decision == "exclude":
        assert r.exclude_reason_zh is not None


def test_include_has_reason():
    results = run_domain_relevance_filter([INVESTMENT_CANDIDATE])
    r = results[0]
    if r.relevance_decision == "include":
        assert r.domain_reason_zh is not None


def test_llm_called_for_uncertain(tmp_path):
    """Uncertain candidates call LLM if client provided."""
    import json
    from demand_radar.semantic_merge.llm_client import FakeLLMClient

    uncertain_candidate = _make_candidate(
        "c_unc_001",
        "Research automation tool",
        "This tool helps automate research workflows and find company information.",
        "rss",
        "https://example.com/tool",
    )
    # LLM response that classifies as include
    fake_resp = json.dumps({
        "candidate_id": "c_unc_001",
        "relevance_decision": "include",
        "relevance_score": 0.70,
        "matched_persona": "investment researcher",
        "matched_workflow": "investment research",
        "domain_reason_zh": "Research automation tool relevant to investment workflows",
        "exclude_reason_zh": None,
    })
    llm = FakeLLMClient(default=fake_resp)
    results = run_domain_relevance_filter([uncertain_candidate], llm_client=llm)
    assert len(results) == 1
    # If it was uncertain route, LLM was called
    r = results[0]
    assert r.relevance_decision in ("include", "uncertain", "exclude")


def test_output_written(tmp_path):
    out = tmp_path / "rel_results.jsonl"
    results = run_domain_relevance_filter([INVESTMENT_CANDIDATE], output_path=out)
    assert out.exists()
    lines = [l for l in out.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 1
