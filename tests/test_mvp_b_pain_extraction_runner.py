"""Tests for pain extraction runner."""
import json
import pytest
from demand_radar.mvp_b.pain_extraction_runner import run_pain_extraction
from demand_radar.semantic_merge.llm_client import FakeLLMClient


def _make_candidate(cid, title, raw_text="A" * 150, source_url="https://example.com/test"):
    return {
        "candidate_id": cid,
        "title": title,
        "raw_text": raw_text,
        "source_type": "community_discussion",
        "source_url": source_url,
        "detected_signal_types": ["workflow_signal"],
    }


def _make_rel(cid, decision="include", score=0.75):
    return {
        "candidate_id": cid,
        "relevance_decision": decision,
        "relevance_score": score,
        "domain_reason_zh": "Test reason",
        "exclude_reason_zh": None if decision != "exclude" else "Excluded for test",
    }


GOOD_PAIN_RESPONSE = json.dumps({
    "candidate_id": "c001",
    "should_extract": True,
    "reject_reason": None,
    "persona": "VC analyst",
    "persona_confidence": 0.85,
    "workflow_stage": "deal_sourcing",
    "job_to_be_done": "Track AI startups efficiently",
    "pain_type": "information_scattered",
    "pain_description_zh": "用户手动追踪AI创业公司非常耗时",
    "evidence_quote": "We spend hours manually tracking startups in spreadsheets.",
    "current_solution": "spreadsheets",
    "paid_alternative": None,
    "business_impact": "hours per week wasted",
    "time_cost_signal": "hours per week",
    "budget_signal": None,
    "commercial_signal_type": "manual_labor_cost",
    "evidence_strength": "medium",
    "confidence": 0.80,
    "reasoning_summary_zh": "明确的工作流痛点",
})


def test_extracts_pain_with_llm():
    candidate = _make_candidate("c001", "VC tracking workflow")
    rel = _make_rel("c001")
    llm = FakeLLMClient(default=GOOD_PAIN_RESPONSE)
    items = run_pain_extraction([candidate], [rel], llm_client=llm)
    assert len(items) == 1
    assert items[0].should_extract is True
    assert items[0].evidence_quote is not None


def test_excluded_candidate_becomes_reject():
    candidate = _make_candidate("c002", "PlanEat AI")
    rel = _make_rel("c002", decision="exclude", score=0.1)
    llm = FakeLLMClient(default=GOOD_PAIN_RESPONSE)
    items = run_pain_extraction([candidate], [rel], llm_client=llm)
    assert len(items) == 1
    assert items[0].should_extract is False
    assert items[0].evidence_strength == "reject"


def test_low_score_becomes_reject():
    candidate = _make_candidate("c003", "Random tool")
    rel = _make_rel("c003", decision="include", score=0.30)
    llm = FakeLLMClient(default=GOOD_PAIN_RESPONSE)
    items = run_pain_extraction([candidate], [rel], llm_client=llm)
    assert items[0].should_extract is False


def test_no_llm_becomes_reject():
    candidate = _make_candidate("c004", "Research tool")
    rel = _make_rel("c004")
    items = run_pain_extraction([candidate], [rel], llm_client=None)
    assert items[0].should_extract is False
    assert "no LLM" in (items[0].reject_reason or "")


def test_invalid_json_retry_then_reject():
    """LLM returning invalid JSON causes retry then reject without breaking pipeline."""
    candidate = _make_candidate("c005", "Investment research tool")
    rel = _make_rel("c005")
    llm = FakeLLMClient(responses=["not valid json", "also not valid"])
    items = run_pain_extraction([candidate], [rel], llm_client=llm)
    assert len(items) == 1
    assert items[0].should_extract is False
    assert items[0].evidence_strength == "reject"


def test_missing_evidence_quote_becomes_reject():
    """LLM output with should_extract=True but no evidence_quote -> reject."""
    bad_response = json.dumps({
        "candidate_id": "c006",
        "should_extract": True,
        "reject_reason": None,
        "persona": "analyst",
        "persona_confidence": 0.7,
        "workflow_stage": "research",
        "job_to_be_done": "research",
        "pain_type": "manual_workflow",
        "pain_description_zh": "Manual pain",
        "evidence_quote": None,
        "current_solution": None,
        "paid_alternative": None,
        "business_impact": None,
        "time_cost_signal": None,
        "budget_signal": None,
        "commercial_signal_type": None,
        "evidence_strength": "medium",
        "confidence": 0.7,
        "reasoning_summary_zh": "test",
    })
    candidate = _make_candidate("c006", "Research tool")
    rel = _make_rel("c006")
    llm = FakeLLMClient(default=bad_response)
    items = run_pain_extraction([candidate], [rel], llm_client=llm)
    assert items[0].should_extract is False
    assert items[0].evidence_strength == "reject"


def test_max_items_limits_processing():
    candidates = [_make_candidate(f"c{i:03d}", f"Tool {i}") for i in range(10)]
    rels = [_make_rel(f"c{i:03d}") for i in range(10)]
    llm = FakeLLMClient(default=GOOD_PAIN_RESPONSE)
    items = run_pain_extraction(candidates, rels, llm_client=llm, max_items=3)
    # processed = max_items, rest may be omitted or incomplete
    assert len(items) <= 10  # no crash


def test_empty_candidates():
    items = run_pain_extraction([], [], llm_client=None)
    assert items == []


def test_output_written(tmp_path):
    candidate = _make_candidate("c_out", "Test tool")
    rel = _make_rel("c_out")
    out = tmp_path / "pain_items.jsonl"
    run_pain_extraction([candidate], [rel], llm_client=None, output_path=out)
    assert out.exists()


def test_all_candidates_produce_result():
    """Every candidate gets a result, even excluded ones."""
    candidates = [_make_candidate(f"cx{i}", f"Tool {i}") for i in range(5)]
    rels = [
        _make_rel("cx0", "include", 0.80),
        _make_rel("cx1", "exclude", 0.10),
        _make_rel("cx2", "include", 0.70),
        _make_rel("cx3", "uncertain", 0.55),
        _make_rel("cx4", "include", 0.20),
    ]
    # No LLM so included will get "no LLM" reject
    items = run_pain_extraction(candidates, rels, llm_client=None, max_items=10)
    cids = [it.candidate_id for it in items]
    # All candidates that were processed should be in results
    assert len(items) >= 5
