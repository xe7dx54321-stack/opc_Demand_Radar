"""Candidate preflight checks and repair for LLM semantic merge (Stage 2.9C).

Validates and repairs ClusterMergeCandidate records before they are sent to
the LLM, catching issues that would cause API failures or low-quality
prompts (e.g. missing field_scores, blank cluster IDs).

Note: The ClusterMergeCandidate schema enforces similarity_score as float,
so None similarity is caught at schema level.  We still check for quality
issues like empty field_scores or blank cluster IDs at runtime.
"""
from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any

from pydantic import BaseModel

from demand_radar.clustering.merge_schema import ClusterMergeCandidate
from demand_radar.state.raw_store import utc_now_iso


class LLMCandidatePreflightResult(BaseModel):
    """Result of preflight checks for a single merge candidate."""

    merge_candidate_id: str
    cluster_id_a: str
    cluster_id_b: str
    status: str  # ok | repaired | invalid
    repair_actions: list[str] = []
    invalid_reasons: list[str] = []
    created_at: str = ""

    def model_post_init(self, __context: Any) -> None:
        if not self.created_at:
            object.__setattr__(self, "created_at", utc_now_iso())


def run_candidate_preflight(
    candidates: list[ClusterMergeCandidate],
    *,
    allow_missing_similarity: bool = False,
    missing_similarity_action: str = "repair",
) -> tuple[list[ClusterMergeCandidate], list[LLMCandidatePreflightResult]]:
    """Check and repair candidates.  Returns (valid candidates, results).

    Parameters
    ----------
    candidates:
        Raw merge candidates.
    allow_missing_similarity:
        If True, skip similarity checks.
    missing_similarity_action:
        Kept for API compatibility; behavior depends on what is feasible.
    """
    out_candidates: list[ClusterMergeCandidate] = []
    results: list[LLMCandidatePreflightResult] = []

    for cand in candidates:
        actions: list[str] = []
        invalids: list[str] = []

        # ── 1. Cluster IDs must be non-blank ──────────────────────────────
        for field in ("cluster_id_a", "cluster_id_b"):
            val = getattr(cand, field, None) or ""
            if not str(val).strip():
                invalids.append(f"{field} is empty or missing")

        # ── 2. field_scores ───────────────────────────────────────────────
        fs = getattr(cand, "field_scores", None) or {}
        if not fs and not allow_missing_similarity:
            # Non-fatal: note it. The prompt will still work without scores.
            actions.append("field_scores is empty; LLM will judge from text fields only")

        # ── 3. merge_reason_zh ────────────────────────────────────────────
        reason = getattr(cand, "merge_reason_zh", None) or ""
        if not reason.strip():
            actions.append("merge_reason_zh is empty; LLM will judge independently")

        # ── 4. Determine status ───────────────────────────────────────────
        if invalids:
            status = "invalid"
        elif actions:
            status = "repaired"
        else:
            status = "ok"

        result = LLMCandidatePreflightResult(
            merge_candidate_id=cand.merge_candidate_id,
            cluster_id_a=cand.cluster_id_a,
            cluster_id_b=cand.cluster_id_b,
            status=status,
            repair_actions=actions,
            invalid_reasons=invalids,
        )
        results.append(result)

        if status != "invalid":
            out_candidates.append(cand)

    return out_candidates, results


# ── Persistence helpers ────────────────────────────────────────────────────────

def write_preflight_results(
    results: list[LLMCandidatePreflightResult],
    path: str | Path = "data/processed/llm_candidate_preflight_results.jsonl",
) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [r.model_dump_json(by_alias=False) for r in results]
    out.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def write_invalid_candidates(
    candidates: list[ClusterMergeCandidate],
    results: list[LLMCandidatePreflightResult],
    path: str | Path = "data/quarantine/invalid_llm_merge_candidates.jsonl",
) -> None:
    """Write invalid candidates together with their preflight reasons."""
    invalid_ids = {r.merge_candidate_id for r in results if r.status == "invalid"}
    invalid_cands = [c for c in candidates if c.merge_candidate_id in invalid_ids]
    invalid_results = {r.merge_candidate_id: r for r in results if r.status == "invalid"}

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for cand in invalid_cands:
        rec = cand.model_dump()
        pf = invalid_results.get(cand.merge_candidate_id)
        rec["preflight_invalid_reasons"] = pf.invalid_reasons if pf else []
        lines.append(json.dumps(rec, ensure_ascii=False))
    out.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")