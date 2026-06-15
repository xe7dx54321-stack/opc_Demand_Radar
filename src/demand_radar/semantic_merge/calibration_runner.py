"""Stage 2.9C/D calibration runner.

Runs the LLM semantic merge judge with calibrated settings:
- candidate preflight (repair / invalidate bad candidates)
- calibrated prompt (v2, versioned via prompt_version config)
- split gate policy (auto_reject threshold 0.75, auto_confirm 0.82)
- versioned cache keys (prompt_version + provider + gate_policy_version)
- no_cache / force_rerun modes (Stage 2.9D)

Outputs go to calibrated_llm_* paths to preserve 2.9B results.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from demand_radar.clustering.cluster_store import load_demand_clusters
from demand_radar.clustering.merge_store import load_merge_candidates
from demand_radar.config.load_config import load_yaml
from demand_radar.semantic_merge.candidate_preflight import (
    LLMCandidatePreflightResult,
    run_candidate_preflight,
    write_invalid_candidates,
    write_preflight_results,
)
from demand_radar.semantic_merge.exception_queue import (
    SemanticMergeGateConfig,
    config_from_dict,
    determine_auto_action,
)
from demand_radar.semantic_merge.llm_cache import CacheStats, LLMSemanticMergeCache
from demand_radar.semantic_merge.llm_client import BaseLLMClient, make_llm_client
from demand_radar.semantic_merge.llm_judge_runner import _build_user_prompt, _failure_judgment
from demand_radar.semantic_merge.llm_output_parser import LLMParseError, parse_llm_output
from demand_radar.semantic_merge.semantic_merge_schema import SemanticMergeJudgment
from demand_radar.semantic_merge.semantic_merge_store import (
    build_human_exception_queue,
    write_human_exception_items,
    write_semantic_merge_judgments,
)
from demand_radar.state.raw_store import next_ids

CALIBRATED_JUDGMENTS_PATH = Path("data/processed/calibrated_llm_semantic_merge_judgments.jsonl")
CALIBRATED_EXCEPTIONS_PATH = Path("data/processed/calibrated_llm_human_exception_queue.jsonl")
CALIBRATED_GROUPS_PATH = Path("data/processed/calibrated_llm_ai_reviewed_cluster_groups.jsonl")
PREFLIGHT_RESULTS_PATH = Path("data/processed/llm_candidate_preflight_results.jsonl")
INVALID_CANDIDATES_PATH = Path("data/quarantine/invalid_llm_merge_candidates.jsonl")

DEFAULT_PROMPT_V2 = "prompts/semantic_merge_judge_v2.md"
DEFAULT_PROMPT_V1 = "prompts/semantic_merge_judge.md"


def _build_system_prompt_calibrated(config: dict) -> tuple[str, str]:
    """Load calibrated prompt v2; fall back to v1. Returns (prompt_text, prompt_version)."""
    semantic = config.get("semantic_merge", {})
    cal_conf = semantic.get("calibration", {})
    prompt_version = cal_conf.get("prompt_version", "semantic_merge_judge_v2")

    candidate_path = Path(f"prompts/{prompt_version}.md")
    if candidate_path.exists():
        return candidate_path.read_text(encoding="utf-8").strip(), prompt_version
    if Path(DEFAULT_PROMPT_V2).exists():
        return Path(DEFAULT_PROMPT_V2).read_text(encoding="utf-8").strip(), "semantic_merge_judge_v2"
    if Path(DEFAULT_PROMPT_V1).exists():
        return Path(DEFAULT_PROMPT_V1).read_text(encoding="utf-8").strip(), "v1"
    return (
        "You are a demand-cluster merge judge. "
        "Output only a JSON object: decision, confidence, reason_zh, "
        "evidence_alignment_zh, workflow_judgment_zh, suggested_group_title_zh, "
        "suggested_group_summary_zh, conflict_flags.",
        "fallback",
    )


def _calibrated_judgment(
    judgment_id: str,
    candidate: Any,
    cluster_a: Any,
    cluster_b: Any,
    client: BaseLLMClient,
    gate_config: SemanticMergeGateConfig,
    system_prompt: str,
    cache: LLMSemanticMergeCache,
    model: str,
) -> SemanticMergeJudgment:
    cached = cache.get(candidate.merge_candidate_id, candidate.cluster_id_a, candidate.cluster_id_b, model)
    if cached is not None:
        data = cached
    else:
        user_prompt = _build_user_prompt(candidate, cluster_a, cluster_b)
        try:
            raw = client.complete(system_prompt, user_prompt)
            data = parse_llm_output(raw)
            cache.set(candidate.merge_candidate_id, candidate.cluster_id_a, candidate.cluster_id_b, model, data)
        except (LLMParseError, Exception) as exc:
            return _failure_judgment(judgment_id, candidate, str(exc), getattr(client, "provider", "llm"), gate_config)

    try:
        decision = str(data["decision"])
        confidence = float(data["confidence"])
        reason_zh = str(data.get("reason_zh", "")).strip()
        evidence_alignment_zh = str(data.get("evidence_alignment_zh", "")).strip() or None
        workflow_judgment_zh = str(data.get("workflow_judgment_zh", "")).strip() or None
        title = str(data.get("suggested_group_title_zh", "")).strip() or None
        summary_zh = str(data.get("suggested_group_summary_zh", "")).strip() or None
        flags = [str(f).strip() for f in (data.get("conflict_flags") or []) if str(f).strip()]
        auto_action = determine_auto_action(
            decision=decision,
            confidence=confidence,
            conflict_flags=flags,
            suggested_group_title_zh=title,
            suggested_group_summary_zh=summary_zh,
            reason_zh=reason_zh,
            config=gate_config,
            evidence_alignment_zh=evidence_alignment_zh,
            workflow_judgment_zh=workflow_judgment_zh,
        )
        return SemanticMergeJudgment(
            judgment_id=judgment_id,
            merge_candidate_id=candidate.merge_candidate_id,
            cluster_id_a=candidate.cluster_id_a,
            cluster_id_b=candidate.cluster_id_b,
            decision=decision,
            confidence=confidence,
            reason_zh=reason_zh,
            evidence_alignment_zh=evidence_alignment_zh,
            workflow_judgment_zh=workflow_judgment_zh,
            suggested_group_title_zh=title,
            suggested_group_summary_zh=summary_zh,
            conflict_flags=flags,
            auto_action=auto_action,
            judge_mode="llm",
        )
    except Exception as exc:
        return _failure_judgment(judgment_id, candidate, str(exc), "llm", gate_config)


def _make_preflight_exception(
    judgment_id: str,
    candidate: Any,
    gate_config: SemanticMergeGateConfig,
    reasons: list[str] | None = None,
) -> SemanticMergeJudgment:
    reason = "preflight_invalid: " + "; ".join(reasons) if reasons else "preflight_invalid"
    auto_action = determine_auto_action(
        decision="maybe_merge",
        confidence=0.0,
        conflict_flags=["weak_evidence"],
        suggested_group_title_zh=None,
        suggested_group_summary_zh=None,
        reason_zh=reason,
        config=gate_config,
    )
    return SemanticMergeJudgment(
        judgment_id=judgment_id,
        merge_candidate_id=candidate.merge_candidate_id,
        cluster_id_a=candidate.cluster_id_a,
        cluster_id_b=candidate.cluster_id_b,
        decision="maybe_merge",
        confidence=0.0,
        reason_zh=reason,
        evidence_alignment_zh=None,
        workflow_judgment_zh=None,
        conflict_flags=["weak_evidence", "preflight_invalid"],
        auto_action=auto_action,
        judge_mode="preflight_invalid",
    )


def run_calibrated_llm_judge(
    candidates_path: str | Path = "data/processed/cluster_merge_candidates.jsonl",
    clusters_path: str | Path = "data/processed/demand_clusters.jsonl",
    judgments_path: str | Path = CALIBRATED_JUDGMENTS_PATH,
    exceptions_path: str | Path = CALIBRATED_EXCEPTIONS_PATH,
    preflight_results_path: str | Path = PREFLIGHT_RESULTS_PATH,
    invalid_candidates_path: str | Path = INVALID_CANDIDATES_PATH,
    config_path: str | Path = "configs/semantic_merge_config.yaml",
    cache_path: str | Path = "data/cache/llm_semantic_merge_cache.jsonl",
    client: BaseLLMClient | None = None,
    no_cache: bool = False,
    force_rerun: bool = False,
    clear_cache_before: bool = False,
) -> tuple[list[SemanticMergeJudgment], list[LLMCandidatePreflightResult], CacheStats]:
    """Run calibrated LLM semantic merge judge for Stage 2.9C/D.

    Args:
        no_cache: Do not read from cache; still write new results.
        force_rerun: Do not read from cache; overwrite existing cache entries.
        clear_cache_before: Delete the entire cache file before running.

    Returns:
        (judgments, preflight_results, cache_stats)
    """
    config = load_yaml(config_path)
    semantic_config = config.get("semantic_merge", {})
    gate_config = config_from_dict(config)

    batch_conf = semantic_config.get("batch", {})
    cache_enabled = bool(batch_conf.get("cache_enabled", True))
    config_force_rerun = bool(batch_conf.get("force_rerun", False))
    max_candidates = int(batch_conf.get("max_candidates_per_run", 200)) if batch_conf.get("max_candidates_per_run") else None

    # CLI flags override config
    effective_force_rerun = force_rerun or config_force_rerun
    effective_no_cache = no_cache or effective_force_rerun

    cal_conf = semantic_config.get("calibration", {})
    prompt_version = cal_conf.get("prompt_version", "semantic_merge_judge_v2")
    gate_policy_version = cal_conf.get("gate_policy_version", "semantic_merge_gate_v1")

    preflight_conf = semantic_config.get("candidate_preflight", {})
    preflight_enabled = bool(preflight_conf.get("enabled", True))
    allow_missing_sim = bool(preflight_conf.get("allow_missing_similarity_score", False))
    missing_sim_action = str(preflight_conf.get("missing_similarity_action", "repair"))

    if client is None:
        llm_conf = semantic_config.get("llm", {})
        provider = llm_conf.get("provider", "openai_compatible")
        client = make_llm_client(provider, semantic_config)
    else:
        provider = getattr(client, "provider", "fake")

    model = getattr(client, "model", "fake")
    system_prompt, resolved_prompt_version = _build_system_prompt_calibrated(config)

    # Build cache with versioned key
    cache = LLMSemanticMergeCache(
        path=cache_path,
        enabled=cache_enabled and not effective_no_cache or (cache_enabled and effective_force_rerun),
        no_read=effective_no_cache,
        force_rerun=effective_force_rerun,
        prompt_version=resolved_prompt_version,
        provider=provider,
        gate_policy_version=gate_policy_version,
    )

    if clear_cache_before:
        removed = cache.clear()
        # Re-init cache after clear (empty store)
        cache = LLMSemanticMergeCache(
            path=cache_path,
            enabled=cache_enabled,
            no_read=effective_no_cache,
            force_rerun=effective_force_rerun,
            prompt_version=resolved_prompt_version,
            provider=provider,
            gate_policy_version=gate_policy_version,
        )

    raw_candidates = load_merge_candidates(candidates_path)
    if max_candidates:
        raw_candidates = raw_candidates[:max_candidates]

    # ---- Preflight ----
    if preflight_enabled:
        valid_candidates, preflight_results = run_candidate_preflight(
            raw_candidates,
            allow_missing_similarity=allow_missing_sim,
            missing_similarity_action=missing_sim_action,
        )
        write_preflight_results(preflight_results, preflight_results_path)
        write_invalid_candidates(raw_candidates, preflight_results, invalid_candidates_path)
    else:
        valid_candidates = raw_candidates
        preflight_results = []

    invalid_ids = {r.merge_candidate_id for r in preflight_results if r.status == "invalid"}

    clusters = load_demand_clusters(clusters_path)
    cluster_by_id = {c.cluster_id: c for c in clusters}

    judgment_ids = next_ids("calibrated_llm_judgment", [], len(raw_candidates))

    judgments: list[SemanticMergeJudgment] = []
    preflight_by_id = {r.merge_candidate_id: r for r in preflight_results}

    for judgment_id, candidate in zip(judgment_ids, raw_candidates, strict=True):
        if candidate.merge_candidate_id in invalid_ids:
            pf = preflight_by_id.get(candidate.merge_candidate_id)
            reasons = pf.invalid_reasons if pf else ["preflight_invalid"]
            judgments.append(_make_preflight_exception(judgment_id, candidate, gate_config, reasons))
            continue

        cluster_a = cluster_by_id.get(candidate.cluster_id_a)
        cluster_b = cluster_by_id.get(candidate.cluster_id_b)
        if cluster_a is None or cluster_b is None:
            reason = "\u5408\u5e76\u5019\u9009\u5f15\u7528\u7684\u9700\u6c42\u4e3b\u9898\u4e0d\u5b58\u5728\uff0c\u9700\u8981\u4eba\u5de5\u68c0\u67e5\u6570\u636e\u72b6\u6001\u3002"
            auto_action = determine_auto_action(
                decision="maybe_merge", confidence=0.0, conflict_flags=["weak_evidence"],
                suggested_group_title_zh=None, suggested_group_summary_zh=None,
                reason_zh=reason, config=gate_config,
            )
            judgments.append(SemanticMergeJudgment(
                judgment_id=judgment_id, merge_candidate_id=candidate.merge_candidate_id,
                cluster_id_a=candidate.cluster_id_a, cluster_id_b=candidate.cluster_id_b,
                decision="maybe_merge", confidence=0.0, reason_zh=reason,
                evidence_alignment_zh="\u7f3a\u5c11\u53ef\u5bf9\u9f50\u7684\u9700\u6c42\u4e3b\u9898\u8bc1\u636e\u3002",
                workflow_judgment_zh="\u65e0\u6cd5\u5224\u65ad\u5de5\u4f5c\u6d41\u5173\u7cfb\u3002",
                conflict_flags=["weak_evidence"], auto_action=auto_action, judge_mode="llm",
            ))
        else:
            pf = preflight_by_id.get(candidate.merge_candidate_id)
            if pf and pf.status == "repaired":
                use_candidate = next(
                    (c for c in valid_candidates if c.merge_candidate_id == candidate.merge_candidate_id),
                    candidate,
                )
            else:
                use_candidate = candidate

            judgments.append(_calibrated_judgment(
                judgment_id, use_candidate, cluster_a, cluster_b,
                client, gate_config, system_prompt, cache, model,
            ))

    write_semantic_merge_judgments(judgments, judgments_path)
    exceptions = build_human_exception_queue(judgments)
    write_human_exception_items(exceptions, exceptions_path)
    return judgments, preflight_results, cache.stats


def build_calibrated_ai_reviewed_groups(
    clusters_path: str | Path = "data/processed/demand_clusters.jsonl",
    judgments_path: str | Path = CALIBRATED_JUDGMENTS_PATH,
    groups_path: str | Path = CALIBRATED_GROUPS_PATH,
    invalid_groups_path: str | Path = "data/quarantine/invalid_calibrated_ai_reviewed_groups.jsonl",
) -> list:
    from demand_radar.semantic_merge.semantic_merge_store import build_ai_reviewed_cluster_groups
    return build_ai_reviewed_cluster_groups(
        clusters_path=clusters_path,
        judgments_path=judgments_path,
        groups_path=groups_path,
        invalid_groups_path=invalid_groups_path,
    )
