"""Stage 2.9C calibration report: LLM vs calibrated_LLM comparison."""
from __future__ import annotations

import statistics
from collections import Counter
from pathlib import Path

from pydantic import BaseModel

from demand_radar.semantic_merge.candidate_preflight import LLMCandidatePreflightResult
from demand_radar.semantic_merge.calibration_runner import (
    CALIBRATED_EXCEPTIONS_PATH,
    CALIBRATED_GROUPS_PATH,
    CALIBRATED_JUDGMENTS_PATH,
    PREFLIGHT_RESULTS_PATH,
)
from demand_radar.semantic_merge.semantic_merge_schema import SemanticMergeJudgment
from demand_radar.semantic_merge.semantic_merge_store import (
    load_ai_reviewed_cluster_groups,
    load_semantic_merge_judgments,
)
from demand_radar.state.raw_store import utc_now_iso

LLM_JUDGMENTS_PATH = Path("data/processed/llm_semantic_merge_judgments.jsonl")
LLM_GROUPS_PATH = Path("data/processed/llm_ai_reviewed_cluster_groups.jsonl")


class CalibrationReportSummary(BaseModel):
    merge_candidates: int
    prev_auto_confirmed: int
    cal_auto_confirmed: int
    prev_auto_rejected: int
    cal_auto_rejected: int
    prev_human_exceptions: int
    cal_human_exceptions: int
    prev_exception_rate: float | None
    cal_exception_rate: float | None
    prev_ai_groups: int
    cal_ai_groups: int
    preflight_ok: int
    preflight_repaired: int
    preflight_invalid: int
    rejects_unlocked: int
    confirms_unlocked: int
    # Cache metadata (Stage 2.9D)
    prompt_version: str = "unknown"
    gate_policy_version: str = "unknown"
    provider: str = "unknown"
    cache_enabled: bool = True
    cache_reads: int = 0
    cache_writes: int = 0
    cache_bypassed: int = 0
    stale_cache_prevented: int = 0
    force_rerun: bool = False
    no_cache: bool = False
    clear_cache_used: bool = False
    # Failure stats (Stage 2.9E)
    llm_call_failures: int = 0
    truncated_outputs: int = 0
    parse_errors: int = 0
    repaired_outputs: int = 0


def _load_judgments_safe(path: Path) -> list[SemanticMergeJudgment]:
    if not path.exists():
        return []
    return load_semantic_merge_judgments(path)


def _load_preflight(path: Path) -> list[LLMCandidatePreflightResult]:
    import json
    if not path.exists():
        return []
    results = []
    for line in path.read_text(encoding="utf-8").strip().splitlines():
        if line.strip():
            results.append(LLMCandidatePreflightResult(**json.loads(line)))
    return results


def _exception_rate(total: int, exceptions: int) -> float | None:
    if total == 0:
        return None
    return round(exceptions / total, 3)


def _conf_stats(judgments: list[SemanticMergeJudgment], decision: str) -> dict:
    vals = [j.confidence for j in judgments if j.decision == decision]
    if not vals:
        return {"count": 0, "min": None, "p25": None, "mean": None, "median": None, "p75": None, "max": None}
    sorted_vals = sorted(vals)
    n = len(sorted_vals)
    return {
        "count": n,
        "min": round(sorted_vals[0], 3),
        "p25": round(sorted_vals[n // 4], 3),
        "mean": round(statistics.mean(vals), 3),
        "median": round(statistics.median(vals), 3),
        "p75": round(sorted_vals[min(3 * n // 4, n - 1)], 3),
        "max": round(sorted_vals[-1], 3),
    }


def build_llm_calibration_report(
    prev_judgments_path: Path = LLM_JUDGMENTS_PATH,
    cal_judgments_path: Path = CALIBRATED_JUDGMENTS_PATH,
    prev_groups_path: Path = LLM_GROUPS_PATH,
    cal_groups_path: Path = CALIBRATED_GROUPS_PATH,
    preflight_path: Path = PREFLIGHT_RESULTS_PATH,
    output_path: Path = Path("outputs/llm_semantic_merge_calibration_report.md"),
    cache_stats: "CacheStats | None" = None,
    run_meta: "dict | None" = None,
) -> CalibrationReportSummary:
    from demand_radar.semantic_merge.llm_cache import CacheStats as _CacheStats
    prev_judgments = _load_judgments_safe(prev_judgments_path)
    cal_judgments = _load_judgments_safe(cal_judgments_path)
    preflight_results = _load_preflight(preflight_path)

    prev_groups = load_ai_reviewed_cluster_groups(prev_groups_path) if prev_groups_path.exists() else []
    cal_groups = load_ai_reviewed_cluster_groups(cal_groups_path) if cal_groups_path.exists() else []

    def _count(jlist: list, action: str) -> int:
        return sum(1 for j in jlist if j.auto_action == action)

    n_prev = len(prev_judgments)
    n_cal = len(cal_judgments)

    prev_confirmed = _count(prev_judgments, "auto_confirm")
    cal_confirmed = _count(cal_judgments, "auto_confirm")
    prev_rejected = _count(prev_judgments, "auto_reject")
    cal_rejected = _count(cal_judgments, "auto_reject")
    prev_exceptions = _count(prev_judgments, "human_exception")
    cal_exceptions = _count(cal_judgments, "human_exception")

    pf_ok = sum(1 for r in preflight_results if r.status == "ok")
    pf_repaired = sum(1 for r in preflight_results if r.status == "repaired")
    pf_invalid = sum(1 for r in preflight_results if r.status == "invalid")

    # Candidates unlocked (were exception in prev, now auto in cal)
    prev_by_id = {j.merge_candidate_id: j for j in prev_judgments}
    cal_by_id = {j.merge_candidate_id: j for j in cal_judgments}

    rejects_unlocked = sum(
        1 for cid, cj in cal_by_id.items()
        if cj.auto_action == "auto_reject"
        and prev_by_id.get(cid, cj).auto_action == "human_exception"
    )
    confirms_unlocked = sum(
        1 for cid, cj in cal_by_id.items()
        if cj.auto_action == "auto_confirm"
        and prev_by_id.get(cid, cj).auto_action == "human_exception"
    )

    _meta = run_meta or {}
    _cs = cache_stats

    # Compute failure stats from calibrated judgments (Stage 2.9E)
    _llm_failures = sum(
        1 for j in cal_judgments
        if j.confidence == 0.0 and j.judge_mode == "llm"
    )
    _truncated = sum(
        1 for j in cal_judgments
        if j.confidence == 0.0 and "Cannot extract JSON" in j.reason_zh
    )
    _parse_errors = sum(
        1 for j in cal_judgments
        if j.confidence == 0.0 and "LLM" in j.reason_zh
    )

    summary = CalibrationReportSummary(
        merge_candidates=max(n_prev, n_cal),
        prev_auto_confirmed=prev_confirmed,
        cal_auto_confirmed=cal_confirmed,
        prev_auto_rejected=prev_rejected,
        cal_auto_rejected=cal_rejected,
        prev_human_exceptions=prev_exceptions,
        cal_human_exceptions=cal_exceptions,
        prev_exception_rate=_exception_rate(n_prev, prev_exceptions),
        cal_exception_rate=_exception_rate(n_cal, cal_exceptions),
        prev_ai_groups=len(prev_groups),
        cal_ai_groups=len(cal_groups),
        preflight_ok=pf_ok,
        preflight_repaired=pf_repaired,
        preflight_invalid=pf_invalid,
        rejects_unlocked=rejects_unlocked,
        confirms_unlocked=confirms_unlocked,
        prompt_version=_meta.get("prompt_version", "unknown"),
        gate_policy_version=_meta.get("gate_policy_version", "unknown"),
        provider=_meta.get("provider", "unknown"),
        cache_enabled=_meta.get("cache_enabled", True),
        cache_reads=_cs.reads if _cs else 0,
        cache_writes=_cs.writes if _cs else 0,
        cache_bypassed=_cs.bypassed if _cs else 0,
        stale_cache_prevented=_cs.stale_prevented if _cs else 0,
        force_rerun=_meta.get("force_rerun", False),
        no_cache=_meta.get("no_cache", False),
        clear_cache_used=_meta.get("clear_cache_used", False),
        llm_call_failures=_llm_failures,
        truncated_outputs=_truncated,
        parse_errors=_parse_errors,
        repaired_outputs=0,
    )

    # ── Build report text ─────────────────────────────────────────────────
    lines: list[str] = [
        "# LLM Semantic Merge Calibration Report",
        "",
        "## Summary",
        "",
        f"- Merge candidates: {summary.merge_candidates}",
        f"- Previous LLM auto confirmed: {prev_confirmed}",
        f"- Calibrated LLM auto confirmed: {cal_confirmed}",
        f"- Previous LLM auto rejected: {prev_rejected}",
        f"- Calibrated LLM auto rejected: {cal_rejected}",
        f"- Previous human exceptions: {prev_exceptions}",
        f"- Calibrated human exceptions: {cal_exceptions}",
        f"- Previous exception rate: {summary.prev_exception_rate}",
        f"- Calibrated exception rate: {summary.cal_exception_rate}",
        f"- AI reviewed groups before: {summary.prev_ai_groups}",
        f"- AI reviewed groups after: {summary.cal_ai_groups}",
        f"- Stage 3 readiness before: {'partial' if summary.prev_ai_groups > 0 else 'no'}",
        f"- Stage 3 readiness after: {'yes' if summary.cal_ai_groups >= 8 and (summary.cal_exception_rate or 1) <= 0.45 else 'partial' if summary.cal_ai_groups >= 3 else 'no'}",
        f"- Generated at: {utc_now_iso()}",
        "",
        "## Failure Statistics (Stage 2.9E)",
        "",
        f"- LLM call failures: {summary.llm_call_failures}",
        f"- Truncated outputs detected: {summary.truncated_outputs}",
        f"- Parse errors (LLM output invalid): {summary.parse_errors}",
        f"- Repaired via partial extraction: {summary.repaired_outputs}",
        "",
        "## Cache Metadata (Stage 2.9D)",
        "",
        f"- prompt_version: {summary.prompt_version}",
        f"- gate_policy_version: {summary.gate_policy_version}",
        f"- provider: {summary.provider}",
        f"- cache_enabled: {summary.cache_enabled}",
        f"- cache_reads: {summary.cache_reads}",
        f"- cache_writes: {summary.cache_writes}",
        f"- cache_bypassed: {summary.cache_bypassed}",
        f"- stale_cache_prevented: {summary.stale_cache_prevented}",
        f"- force_rerun: {summary.force_rerun}",
        f"- no_cache: {summary.no_cache}",
        f"- clear_cache_used: {summary.clear_cache_used}",
        "",
        "## Confidence Distribution",
        "",
        "| Decision | Count | Min | P25 | Mean | Median | P75 | Max |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for dec in ("confirm_merge", "reject_merge", "maybe_merge"):
        ps = _conf_stats(prev_judgments, dec)
        cs = _conf_stats(cal_judgments, dec)
        lines.append(
            f"| prev/{dec} | {ps['count']} | {ps['min']} | {ps['p25']} | {ps['mean']} | {ps['median']} | {ps['p75']} | {ps['max']} |"
        )
        lines.append(
            f"| cal/{dec} | {cs['count']} | {cs['min']} | {cs['p25']} | {cs['mean']} | {cs['median']} | {cs['p75']} | {cs['max']} |"
        )

    # Gate outcome breakdown
    lines += [
        "",
        "## Gate Outcome Breakdown",
        "",
        "| Source | Decision | Auto Confirm | Auto Reject | Human Exception |",
        "|---|---|---:|---:|---:|",
    ]
    for source, jlist in [("prev_llm", prev_judgments), ("cal_llm", cal_judgments)]:
        for dec in ("confirm_merge", "reject_merge", "maybe_merge"):
            dec_items = [j for j in jlist if j.decision == dec]
            ac = sum(1 for j in dec_items if j.auto_action == "auto_confirm")
            ar = sum(1 for j in dec_items if j.auto_action == "auto_reject")
            he = sum(1 for j in dec_items if j.auto_action == "human_exception")
            lines.append(f"| {source} | {dec} | {ac} | {ar} | {he} |")

    # Preflight results
    lines += [
        "",
        "## Preflight Results",
        "",
        f"- OK: {pf_ok}",
        f"- Repaired: {pf_repaired}",
        f"- Invalid: {pf_invalid}",
    ]
    if pf_invalid > 0:
        invalid_results = [r for r in preflight_results if r.status == "invalid"]
        reasons = Counter(reason for r in invalid_results for reason in r.invalid_reasons)
        lines.append("- Invalid reasons:")
        for reason, count in reasons.most_common(5):
            lines.append(f"  - {count}x: {reason}")
    if pf_repaired > 0:
        repaired_results = [r for r in preflight_results if r.status == "repaired"]
        for r in repaired_results[:3]:
            lines.append(f"  - {r.merge_candidate_id}: {'; '.join(r.repair_actions)}")

    # Threshold impact
    lines += [
        "",
        "## Threshold Impact",
        "",
        f"- Rejects unlocked by calibrated threshold: {rejects_unlocked}",
        f"- Confirms unlocked by calibrated threshold: {confirms_unlocked}",
        f"- Still in exception: {cal_exceptions}",
    ]

    # Representative examples
    lines += ["", "## Representative Examples", ""]

    cal_confirms = [j for j in cal_judgments if j.auto_action == "auto_confirm"]
    if cal_confirms:
        j = cal_confirms[0]
        lines += [
            "### Auto Confirm Example",
            "",
            f"Candidate: {j.merge_candidate_id}",
            f"Clusters: {j.cluster_id_a} / {j.cluster_id_b}",
            f"Confidence: {j.confidence}",
            f"Reason: {j.reason_zh[:200]}",
            f"Suggested Group Title: {j.suggested_group_title_zh or 'N/A'}",
            "",
        ]

    cal_rejects = [j for j in cal_judgments if j.auto_action == "auto_reject"]
    if cal_rejects:
        j = cal_rejects[0]
        lines += [
            "### Auto Reject Example",
            "",
            f"Candidate: {j.merge_candidate_id}",
            f"Clusters: {j.cluster_id_a} / {j.cluster_id_b}",
            f"Confidence: {j.confidence}",
            f"Reason: {j.reason_zh[:200]}",
            "",
        ]

    cal_exceptions_list = [j for j in cal_judgments if j.auto_action == "human_exception"]
    if cal_exceptions_list:
        j = cal_exceptions_list[0]
        lines += [
            "### Human Exception Example",
            "",
            f"Candidate: {j.merge_candidate_id}",
            f"Decision: {j.decision}",
            f"Confidence: {j.confidence}",
            f"Reason: {j.reason_zh[:200]}",
            f"Conflict Flags: {j.conflict_flags}",
            "",
        ]

    # Repaired example
    repaired_pf = [r for r in preflight_results if r.status == "repaired"]
    if repaired_pf:
        r = repaired_pf[0]
        lines += [
            "### Repaired Candidate Example",
            "",
            f"Candidate: {r.merge_candidate_id}",
            f"Repair actions: {'; '.join(r.repair_actions)}",
            "",
        ]

    # Recommendation
    can_enter = summary.cal_ai_groups >= 5 and (summary.cal_exception_rate or 1.0) <= 0.45
    near_enter = summary.cal_ai_groups >= 3
    lines += [
        "## Recommendation",
        "",
        f"- Enter Stage 3: {'yes' if can_enter else 'partial' if near_enter else 'no'}",
        f"- AI reviewed groups: {summary.cal_ai_groups} (target >= 5)",
        f"- Exception rate: {summary.cal_exception_rate} (target <= 0.45)",
    ]
    if not can_enter:
        lines.append("- Consider further prompt calibration or threshold adjustment if groups < 5.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary