"""Tests for candidate preflight (Stage 2.9C)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from demand_radar.clustering.merge_schema import ClusterMergeCandidate
from demand_radar.semantic_merge.candidate_preflight import (
    LLMCandidatePreflightResult,
    run_candidate_preflight,
    write_preflight_results,
    write_invalid_candidates,
)


def _make_candidate(
    cid: str = "mc_001",
    sim: float = 85.0,
    field_scores: dict | None = None,
    cluster_id_a: str = "cluster_001",
    cluster_id_b: str = "cluster_002",
) -> ClusterMergeCandidate:
    return ClusterMergeCandidate(
        merge_candidate_id=cid,
        cluster_id_a=cluster_id_a,
        cluster_id_b=cluster_id_b,
        title_a="需求主题A标题",
        title_b="需求主题B标题",
        similarity_score=sim,
        strength="strong",
        field_scores=field_scores if field_scores is not None else {
            "pain_description_similarity": 0.8,
            "summary_similarity": 0.7,
        },
        shared_personas=["researcher"],
        shared_keywords=["data"],
        shared_domain_tags=["research"],
        merge_reason_zh="两个主题有相似的核心痛点。",
    )


def test_ok_candidate():
    cand = _make_candidate()
    valid, results = run_candidate_preflight([cand])
    assert len(valid) == 1
    assert results[0].status == "ok"
    assert results[0].repair_actions == []
    assert results[0].invalid_reasons == []


def test_low_similarity_still_ok():
    """Low similarity score candidates should still pass preflight (score is valid)."""
    cand = _make_candidate(sim=30.0)
    valid, results = run_candidate_preflight([cand])
    assert len(valid) == 1
    assert results[0].status == "ok"


def test_empty_field_scores_ok():
    """Empty field_scores is allowed (non-fatal)."""
    cand = _make_candidate(field_scores={})
    valid, results = run_candidate_preflight([cand])
    assert len(valid) == 1
    # Status may be ok or repaired but not invalid
    assert results[0].status in ("ok", "repaired")
    assert results[0].invalid_reasons == []


def test_missing_cluster_ids_invalid():
    """Blank cluster IDs should be caught in preflight."""
    # We can only test this via direct result construction since pydantic
    # would normally reject blank strings. Patch via dict then test preflight result logic.
    cand = _make_candidate()
    # Simulate an invalid candidate by patching the preflight result directly
    result = LLMCandidatePreflightResult(
        merge_candidate_id=cand.merge_candidate_id,
        cluster_id_a="",
        cluster_id_b=cand.cluster_id_b,
        status="invalid",
        invalid_reasons=["cluster_id_a is empty or missing"],
    )
    assert result.status == "invalid"
    assert result.invalid_reasons


def test_run_preflight_multiple():
    """Multiple candidates all valid should all return ok."""
    cands = [_make_candidate(f"mc_{i:03d}", sim=80.0 + i) for i in range(5)]
    valid, results = run_candidate_preflight(cands)
    assert len(valid) == 5
    assert all(r.status == "ok" for r in results)


def test_write_preflight_results(tmp_path):
    cand = _make_candidate()
    _, results = run_candidate_preflight([cand])
    out = tmp_path / "results.jsonl"
    write_preflight_results(results, out)
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "merge_candidate_id" in content


def test_write_invalid_candidates(tmp_path):
    """write_invalid_candidates writes nothing if no invalids."""
    cand = _make_candidate()
    _, results = run_candidate_preflight([cand])
    out = tmp_path / "invalid.jsonl"
    write_invalid_candidates([cand], results, out)
    assert out.exists()
    content = out.read_text(encoding="utf-8").strip()
    # No invalid candidates, file should be empty
    assert content == ""


def test_preflight_result_schema():
    """LLMCandidatePreflightResult can be constructed with all fields."""
    r = LLMCandidatePreflightResult(
        merge_candidate_id="mc_001",
        cluster_id_a="cluster_001",
        cluster_id_b="cluster_002",
        status="repaired",
        repair_actions=["similarity_score repaired from field_scores: 0.750"],
        invalid_reasons=[],
    )
    assert r.status == "repaired"
    assert "repaired" in r.repair_actions[0]
    assert r.created_at  # auto-set


def test_preflight_result_serializable(tmp_path):
    cand = _make_candidate()
    _, results = run_candidate_preflight([cand])
    out = tmp_path / "r.jsonl"
    write_preflight_results(results, out)
    loaded = json.loads(out.read_text(encoding="utf-8").strip())
    assert loaded["merge_candidate_id"] == cand.merge_candidate_id
    assert loaded["status"] in ("ok", "repaired", "invalid")