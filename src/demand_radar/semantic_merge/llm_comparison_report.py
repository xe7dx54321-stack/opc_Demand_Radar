"""Stage 2.9 comparison report: rule_based vs LLM semantic merge results."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from pydantic import BaseModel

from demand_radar.semantic_merge.semantic_merge_schema import SemanticMergeJudgment
from demand_radar.semantic_merge.semantic_merge_store import (
    load_ai_reviewed_cluster_groups,
    load_human_exception_items,
    load_semantic_merge_judgments,
)
from demand_radar.state.raw_store import utc_now_iso


class DecisionShift(BaseModel):
    """Counts of how rule_based decisions changed under LLM."""
    rule_confirm_llm_confirm: int = 0
    rule_confirm_llm_reject: int = 0
    rule_confirm_llm_maybe: int = 0
    rule_reject_llm_confirm: int = 0
    rule_reject_llm_reject: int = 0
    rule_reject_llm_maybe: int = 0
    rule_maybe_llm_confirm: int = 0
    rule_maybe_llm_reject: int = 0
    rule_maybe_llm_maybe: int = 0


class ComparisonSummary(BaseModel):
    merge_candidates: int
    rule_based_judgments: int
    llm_judgments: int
    rule_based_auto_confirmed: int
    llm_auto_confirmed: int
    rule_based_auto_rejected: int
    llm_auto_rejected: int
    rule_based_human_exceptions: int
    llm_human_exceptions: int
    rule_based_exception_rate: float | None
    llm_exception_rate: float | None
    rule_based_ai_groups: int
    llm_ai_groups: int
    exception_rate_reduction: float | None
    maybe_to_confirm: int
    maybe_to_reject: int
    confirm_to_reject: int
    reject_to_confirm: int
    llm_failures: int
    low_confidence_llm: int
    shift: DecisionShift
    readiness_source: str
    generated_at: str


def build_semantic_merge_comparison_report(
    rule_judgments_path: str | Path = "data/processed/semantic_merge_judgments.jsonl",
    llm_judgments_path: str | Path = "data/processed/llm_semantic_merge_judgments.jsonl",
    rule_groups_path: str | Path = "data/processed/ai_reviewed_cluster_groups.jsonl",
    llm_groups_path: str | Path = "data/processed/llm_ai_reviewed_cluster_groups.jsonl",
    rule_exceptions_path: str | Path = "data/processed/human_exception_queue.jsonl",
    llm_exceptions_path: str | Path = "data/processed/llm_human_exception_queue.jsonl",
    report_path: str | Path = "outputs/llm_semantic_merge_comparison_report.md",
    run_summary_path: str | Path = "outputs/run_summary.json",
) -> ComparisonSummary:
    rule_judgments = load_semantic_merge_judgments(rule_judgments_path)
    llm_judgments = load_semantic_merge_judgments(llm_judgments_path)
    rule_groups = load_ai_reviewed_cluster_groups(rule_groups_path)
    llm_groups = load_ai_reviewed_cluster_groups(llm_groups_path)
    rule_exceptions = load_human_exception_items(rule_exceptions_path)
    llm_exceptions = load_human_exception_items(llm_exceptions_path)

    rule_by_candidate: dict[str, SemanticMergeJudgment] = {j.merge_candidate_id: j for j in rule_judgments}
    llm_by_candidate: dict[str, SemanticMergeJudgment] = {j.merge_candidate_id: j for j in llm_judgments}
    all_candidates = sorted(set(list(rule_by_candidate) + list(llm_by_candidate)))

    shift = DecisionShift()
    maybe_to_confirm = maybe_to_reject = confirm_to_reject = reject_to_confirm = 0
    llm_failures = low_confidence_llm = 0

    for cid in all_candidates:
        rb = rule_by_candidate.get(cid)
        lm = llm_by_candidate.get(cid)
        if rb is None or lm is None:
            continue
        key = f"rule_{_short(rb.decision)}_llm_{_short(lm.decision)}"
        if hasattr(shift, key):
            setattr(shift, key, getattr(shift, key) + 1)
        if rb.decision == "maybe_merge" and lm.decision == "confirm_merge":
            maybe_to_confirm += 1
        if rb.decision == "maybe_merge" and lm.decision == "reject_merge":
            maybe_to_reject += 1
        if rb.decision == "confirm_merge" and lm.decision == "reject_merge":
            confirm_to_reject += 1
        if rb.decision == "reject_merge" and lm.decision == "confirm_merge":
            reject_to_confirm += 1
        if lm.confidence == 0.0 and "LLM" in (lm.reason_zh or ""):
            llm_failures += 1
        if 0.0 < lm.confidence < 0.70:
            low_confidence_llm += 1

    rule_exc_rate = (len(rule_exceptions) / len(rule_judgments)) if rule_judgments else None
    llm_exc_rate = (len(llm_exceptions) / len(llm_judgments)) if llm_judgments else None
    exc_reduction: float | None = None
    if rule_exc_rate is not None and llm_exc_rate is not None:
        exc_reduction = round(rule_exc_rate - llm_exc_rate, 4)

    readiness_source = "llm" if llm_judgments else "rule_based"
    summary = ComparisonSummary(
        merge_candidates=len(all_candidates),
        rule_based_judgments=len(rule_judgments),
        llm_judgments=len(llm_judgments),
        rule_based_auto_confirmed=sum(1 for j in rule_judgments if j.auto_action == "auto_confirm"),
        llm_auto_confirmed=sum(1 for j in llm_judgments if j.auto_action == "auto_confirm"),
        rule_based_auto_rejected=sum(1 for j in rule_judgments if j.auto_action == "auto_reject"),
        llm_auto_rejected=sum(1 for j in llm_judgments if j.auto_action == "auto_reject"),
        rule_based_human_exceptions=len(rule_exceptions),
        llm_human_exceptions=len(llm_exceptions),
        rule_based_exception_rate=round(rule_exc_rate, 4) if rule_exc_rate is not None else None,
        llm_exception_rate=round(llm_exc_rate, 4) if llm_exc_rate is not None else None,
        rule_based_ai_groups=len(rule_groups),
        llm_ai_groups=len(llm_groups),
        exception_rate_reduction=exc_reduction,
        maybe_to_confirm=maybe_to_confirm,
        maybe_to_reject=maybe_to_reject,
        confirm_to_reject=confirm_to_reject,
        reject_to_confirm=reject_to_confirm,
        llm_failures=llm_failures,
        low_confidence_llm=low_confidence_llm,
        shift=shift,
        readiness_source=readiness_source,
        generated_at=utc_now_iso(),
    )

    _write_report(summary, rule_judgments, llm_judgments, rule_by_candidate, llm_by_candidate, report_path)
    _update_run_summary(summary, run_summary_path)
    return summary


def _write_report(
    summary: ComparisonSummary,
    rule_judgments: list[SemanticMergeJudgment],
    llm_judgments: list[SemanticMergeJudgment],
    rule_by_candidate: dict[str, SemanticMergeJudgment],
    llm_by_candidate: dict[str, SemanticMergeJudgment],
    report_path: str | Path,
) -> None:
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# LLM Semantic Merge Comparison Report",
        "",
        "## Summary",
        "",
        f"- Merge candidates: {summary.merge_candidates}",
        f"- Rule-based judgments: {summary.rule_based_judgments}",
        f"- LLM judgments: {summary.llm_judgments}",
        f"- Rule-based auto confirmed: {summary.rule_based_auto_confirmed}",
        f"- LLM auto confirmed: {summary.llm_auto_confirmed}",
        f"- Rule-based auto rejected: {summary.rule_based_auto_rejected}",
        f"- LLM auto rejected: {summary.llm_auto_rejected}",
        f"- Rule-based human exceptions: {summary.rule_based_human_exceptions}",
        f"- LLM human exceptions: {summary.llm_human_exceptions}",
        f"- Rule-based exception rate: {_pct(summary.rule_based_exception_rate)}",
        f"- LLM exception rate: {_pct(summary.llm_exception_rate)}",
        f"- Rule-based AI reviewed groups: {summary.rule_based_ai_groups}",
        f"- LLM AI reviewed groups: {summary.llm_ai_groups}",
        f"- Readiness source: {summary.readiness_source}",
        f"- Generated at: {summary.generated_at}",
        "",
        "## Decision Shift Matrix",
        "",
        "| Rule-based \\ LLM | confirm | reject | maybe |",
        "|---|---:|---:|---:|",
        f"| confirm | {summary.shift.rule_confirm_llm_confirm} | {summary.shift.rule_confirm_llm_reject} | {summary.shift.rule_confirm_llm_maybe} |",
        f"| reject | {summary.shift.rule_reject_llm_confirm} | {summary.shift.rule_reject_llm_reject} | {summary.shift.rule_reject_llm_maybe} |",
        f"| maybe | {summary.shift.rule_maybe_llm_confirm} | {summary.shift.rule_maybe_llm_reject} | {summary.shift.rule_maybe_llm_maybe} |",
        "",
        "## Improvements",
        "",
        f"- Candidates moved from maybe to auto_confirm: {summary.maybe_to_confirm}",
        f"- Candidates moved from maybe to auto_reject: {summary.maybe_to_reject}",
        f"- New LLM reviewed groups: {summary.llm_ai_groups}",
        f"- Exception rate reduction: {_pct(summary.exception_rate_reduction)}",
        "",
        "## Potential Risks",
        "",
        f"- LLM confirms that rule-based rejected: {summary.reject_to_confirm}",
        f"- LLM rejects that rule-based confirmed: {summary.confirm_to_reject}",
        f"- Low-confidence LLM outputs (< 0.70): {summary.low_confidence_llm}",
        f"- LLM call failures: {summary.llm_failures}",
        "",
        "## Representative Examples",
        "",
    ]

    # maybe → confirm
    examples_added = 0
    for cid, lm in llm_by_candidate.items():
        rb = rule_by_candidate.get(cid)
        if rb and rb.decision == "maybe_merge" and lm.decision == "confirm_merge" and lm.auto_action == "auto_confirm":
            lines += [
                "### 1. Rule-based maybe → LLM confirm",
                "",
                f"Candidate: {cid}",
                f"Clusters: {lm.cluster_id_a} / {lm.cluster_id_b}",
                f"LLM reason: {lm.reason_zh}",
                f"Suggested group title: {lm.suggested_group_title_zh or 'n/a'}",
                "",
            ]
            examples_added += 1
            break
    if examples_added == 0:
        lines += ["### 1. Rule-based maybe → LLM confirm", "", "No examples in this run.", ""]

    # maybe → reject
    examples_added = 0
    for cid, lm in llm_by_candidate.items():
        rb = rule_by_candidate.get(cid)
        if rb and rb.decision == "maybe_merge" and lm.decision == "reject_merge":
            lines += [
                "### 2. Rule-based maybe → LLM reject",
                "",
                f"Candidate: {cid}",
                f"Clusters: {lm.cluster_id_a} / {lm.cluster_id_b}",
                f"LLM reason: {lm.reason_zh}",
                "",
            ]
            examples_added += 1
            break
    if examples_added == 0:
        lines += ["### 2. Rule-based maybe → LLM reject", "", "No examples in this run.", ""]

    # LLM human exception
    from demand_radar.semantic_merge.semantic_merge_store import load_human_exception_items
    llm_exc_items = load_human_exception_items("data/processed/llm_human_exception_queue.jsonl")
    if llm_exc_items:
        item = llm_exc_items[0]
        lines += [
            "### 3. LLM human exception",
            "",
            f"Candidate: {item.merge_candidate_id}",
            f"Reason: {item.exception_reason}",
            f"Conflict flags: {', '.join(item.conflict_flags) or 'none'}",
            "",
        ]
    else:
        lines += ["### 3. LLM human exception", "", "No exceptions in this run.", ""]

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _update_run_summary(summary: ComparisonSummary, summary_path: str | Path) -> None:
    path = Path(summary_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: dict = {}
    if path.exists() and path.read_text(encoding="utf-8").strip():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    existing.update({
        "llm_judgments": summary.llm_judgments,
        "llm_auto_confirmed": summary.llm_auto_confirmed,
        "llm_auto_rejected": summary.llm_auto_rejected,
        "llm_human_exceptions": summary.llm_human_exceptions,
        "llm_exception_rate": summary.llm_exception_rate,
        "llm_ai_groups": summary.llm_ai_groups,
        "exception_rate_reduction": summary.exception_rate_reduction,
        "readiness_source": summary.readiness_source,
        "comparison_generated_at": summary.generated_at,
    })
    path.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _short(decision: str) -> str:
    return {"confirm_merge": "confirm", "reject_merge": "reject", "maybe_merge": "maybe"}.get(decision, decision)


def _pct(rate: float | None) -> str:
    if rate is None:
        return "n/a"
    return f"{rate * 100:.1f}%"
