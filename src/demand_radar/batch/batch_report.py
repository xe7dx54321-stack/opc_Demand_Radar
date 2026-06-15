"""Batch summary report generation for Stage 2.6/2.7."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from demand_radar.batch.batch_schema import BatchSummary, BatchSummaryResult
from demand_radar.batch.batch_summary import build_batch_summary


def build_batch_summary_report(
    report_path: str | Path = "outputs/batch_summary_report.md",
    matrix_path: str | Path = "outputs/batch_quality_matrix.csv",
    summary_path: str | Path = "outputs/run_summary.json",
    **summary_paths: object,
) -> BatchSummaryResult:
    result = build_batch_summary(**summary_paths)
    _write_markdown(result, report_path)
    _write_quality_matrix(result.batches, matrix_path)
    _merge_run_summary(result, summary_path)
    return result


def _write_markdown(result: BatchSummaryResult, report_path: str | Path) -> None:
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    overall = result.overall
    lines = [
        "# Batch Summary Report",
        "",
        "## Overall Summary",
        "",
        f"- Raw signals: {overall.raw_signals}",
        f"- Normalized signals: {overall.normalized_signals}",
        f"- Pain points: {overall.pain_points}",
        f"- Quarantined items: {overall.quarantined_items}",
        f"- Demand clusters: {overall.demand_clusters}",
        f"- Singleton clusters: {overall.singleton_clusters}",
        f"- Merge candidates: {overall.merge_candidates}",
        f"- Human reviewed groups: {overall.reviewed_groups}",
        f"- AI reviewed groups: {overall.ai_reviewed_groups}",
        f"- Total reviewed groups: {overall.total_reviewed_groups}",
        f"- Semantic judgments: {overall.semantic_judgments}",
        f"- Auto confirmed merges: {overall.auto_confirmed_merges}",
        f"- Auto rejected merges: {overall.auto_rejected_merges}",
        f"- Human exceptions: {overall.human_exceptions}",
        f"- Calibration reviews: {overall.calibration_reviews}",
        f"- Cluster reviews: {overall.cluster_reviews}",
        f"- Merge reviews: {overall.merge_reviews}",
        f"- Generated at: {result.generated_at}",
        "",
        "## Batch Breakdown",
        "",
    ]
    for batch in result.batches:
        lines.extend(_batch_lines(batch))
    lines.extend(_quality_matrix_lines(result.batches))
    lines.extend(_readiness_lines(result))
    lines.extend(_truth_scoring_lines())
    lines.extend(_evidence_gap_lines())
    lines.extend(_targeted_expansion_lines())
    lines.extend(_lineage_lines())
    lines.extend(_stage35_lines())
    lines.extend(_real_evidence_lines())
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _batch_lines(batch: BatchSummary) -> list[str]:
    return [
        f"### {batch.batch_id}",
        "",
        f"- Raw signals: {batch.raw_signals}",
        f"- Pain points: {batch.pain_points}",
        f"- Quarantine rate: {_percent(batch.quarantine_rate)}",
        f"- Demand clusters: {batch.demand_clusters}",
        f"- Singleton clusters: {batch.singleton_clusters}",
        f"- Merge candidates: {batch.merge_candidates}",
        f"- Human reviewed groups: {batch.reviewed_groups}",
        f"- AI reviewed groups: {batch.ai_reviewed_groups}",
        f"- Total reviewed groups: {batch.total_reviewed_groups}",
        f"- Semantic judgments: {batch.semantic_judgments}",
        f"- Human exceptions: {batch.human_exceptions}",
        "",
        "Extraction Quality:",
        f"- Good: {batch.good_extractions}",
        f"- Weak: {batch.weak_extractions}",
        f"- False positive: {batch.false_positives}",
        f"- Bad quote: {batch.bad_quotes}",
        f"- Should quarantine: {batch.should_quarantine}",
        "",
        "Observations:",
        (
            f"- 抽取产出率：{_percent(batch.extraction_yield)}；"
            f"单证据主题比例：{_percent(batch.singleton_rate)}；"
            f"合并建议密度：{_percent(batch.merge_candidate_rate)}。"
        ),
        (
            f"- AI 主审：自动确认 {batch.auto_confirmed_merges}，"
            f"自动拒绝 {batch.auto_rejected_merges}，"
            f"人工异常 {batch.human_exceptions}，"
            f"异常率 {_percent(batch.human_exception_rate)}。"
        ),
        "",
    ]


def _quality_matrix_lines(batches: list[BatchSummary]) -> list[str]:
    lines = [
        "## Quality Matrix",
        "",
        (
            "| Batch | Raw | Pain Points | Quarantine Rate | Clusters | Singleton Rate | "
            "Merge Candidates | AI Groups | Total Groups | Human Exceptions | Notes |"
        ),
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for batch in batches:
        lines.append(
            "| "
            f"{batch.batch_id} | {batch.raw_signals} | {batch.pain_points} | "
            f"{_percent(batch.quarantine_rate)} | {batch.demand_clusters} | "
            f"{_percent(batch.singleton_rate)} | {batch.merge_candidates} | "
            f"{batch.ai_reviewed_groups} | {batch.total_reviewed_groups} | "
            f"{batch.human_exceptions} | {_batch_note(batch)} |"
        )
    lines.append("")
    return lines


def _readiness_lines(result: BatchSummaryResult) -> list[str]:
    readiness = result.readiness
    return [
        "## Stage 3 Readiness",
        "",
        f"- Is sample size sufficient? {'yes' if readiness.sample_size_ok else 'no'}",
        f"- Is extraction quality acceptable? {'yes' if readiness.pain_volume_ok else 'no'}",
        f"- Are reviewed groups enough? {'yes' if readiness.group_volume_ok else 'no'}",
        f"- Is human exception rate acceptable? {'yes' if readiness.exception_rate_ok else 'no'}",
        f"- Are auto confirmed groups enough? {'yes' if readiness.auto_confirmed_groups_ok else 'no'}",
        f"- Human exception rate: {_percent(readiness.human_exception_rate)}",
        f"- Auto confirmed groups: {readiness.auto_confirmed_groups}",
        f"- Total reviewed groups: {readiness.total_reviewed_groups}",
        f"- Legacy clustering convergence: {'yes' if readiness.clustering_convergence_ok else 'no'}",
        f"- ready_for_truth_scoring: {readiness.ready_for_truth_scoring}",
        f"- Recommendation: {readiness.recommendation}",
        "",
    ]



def _truth_scoring_lines() -> list[str]:
    """Append Stage 3 Truth Scoring summary from truth_scores.jsonl if it exists."""
    import json
    path = Path("data/processed/truth_scores.jsonl")
    if not path.exists():
        return []
    scores = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            scores.append(json.loads(line))
        except Exception:
            continue
    if not scores:
        return []

    level_counts = {"strong": 0, "medium": 0, "weak": 0, "insufficient": 0}
    action_counts: dict[str, int] = {}
    for s in scores:
        lvl = s.get("truth_level", "insufficient")
        level_counts[lvl] = level_counts.get(lvl, 0) + 1
        act = s.get("recommended_next_action", "")
        action_counts[act] = action_counts.get(act, 0) + 1

    proceed = action_counts.get("proceed_to_fit_scoring", 0)
    ready = "yes" if proceed >= 1 else ("partial" if level_counts.get("medium", 0) + level_counts.get("strong", 0) >= 2 else "no")

    return [
        "",
        "## Stage 3: Truth Scoring",
        "",
        f"- truth_scores: {len(scores)}",
        f"- strong_truth_candidates: {level_counts.get('strong', 0)}",
        f"- medium_truth_candidates: {level_counts.get('medium', 0)}",
        f"- weak_truth_candidates: {level_counts.get('weak', 0)}",
        f"- insufficient_truth_candidates: {level_counts.get('insufficient', 0)}",
        f"- proceed_to_fit_scoring: {proceed}",
        f"- needs_more_evidence: {action_counts.get('needs_more_evidence', 0)}",
        f"- keep_watch: {action_counts.get('keep_watch', 0)}",
        f"- truth_scoring_source: calibrated_llm_ai_reviewed_group",
        f"- ready_for_fit_scoring: {ready}",
        "",
    ]



def _evidence_gap_lines() -> list[str]:
    """Append Stage 3.2 Evidence Gap summary if gap analysis exists."""
    import json
    path = Path("data/processed/evidence_gap_analysis.jsonl")
    if not path.exists():
        return []
    gaps = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            gaps.append(json.loads(line))
        except Exception:
            continue
    if not gaps:
        return []

    by_pri = {"high": 0, "medium": 0, "low": 0}
    total_signals = 0
    plan_path = Path("data/processed/targeted_signal_collection_plan.jsonl")
    if plan_path.exists():
        for line in plan_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                p = json.loads(line)
                total_signals += p.get("target_new_signals", 0)
            except Exception:
                continue
    for g in gaps:
        pri = g.get("priority", "low")
        by_pri[pri] = by_pri.get(pri, 0) + 1

    return [
        "",
        "## Stage 3.2: Evidence Gap Analysis",
        "",
        f"- evidence_gap_candidates: {len(gaps)}",
        f"- high_priority_gaps: {by_pri['high']}",
        f"- medium_priority_gaps: {by_pri['medium']}",
        f"- low_priority_gaps: {by_pri['low']}",
        f"- target_new_signals: {total_signals}",
        "",
    ]


def _write_quality_matrix(batches: list[BatchSummary], matrix_path: str | Path) -> None:
    matrix_path = Path(matrix_path)
    matrix_path.parent.mkdir(parents=True, exist_ok=True)
    with matrix_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "batch_id",
                "raw_signals",
                "pain_points",
                "quarantine_rate",
                "demand_clusters",
                "singleton_rate",
                "merge_candidates",
                "ai_reviewed_groups",
                "total_reviewed_groups",
                "human_exceptions",
                "notes",
            ],
        )
        writer.writeheader()
        for batch in batches:
            writer.writerow(
                {
                    "batch_id": batch.batch_id,
                    "raw_signals": batch.raw_signals,
                    "pain_points": batch.pain_points,
                    "quarantine_rate": _percent(batch.quarantine_rate),
                    "demand_clusters": batch.demand_clusters,
                    "singleton_rate": _percent(batch.singleton_rate),
                    "merge_candidates": batch.merge_candidates,
                    "ai_reviewed_groups": batch.ai_reviewed_groups,
                    "total_reviewed_groups": batch.total_reviewed_groups,
                    "human_exceptions": batch.human_exceptions,
                    "notes": _batch_note(batch),
                }
            )


def _merge_run_summary(result: BatchSummaryResult, summary_path: str | Path) -> None:
    summary_path = Path(summary_path)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if summary_path.exists() and summary_path.read_text(encoding="utf-8").strip():
        existing = json.loads(summary_path.read_text(encoding="utf-8"))
    existing.update(
        {
            "batch_count": len(result.batches),
            "ready_for_truth_scoring": result.readiness.ready_for_truth_scoring,
            "total_reviewed_groups": result.overall.total_reviewed_groups,
            "ai_reviewed_groups": result.overall.ai_reviewed_groups,
            "semantic_judgments": result.overall.semantic_judgments,
            "auto_confirmed_merges": result.overall.auto_confirmed_merges,
            "auto_rejected_merges": result.overall.auto_rejected_merges,
            "human_exceptions": result.overall.human_exceptions,
            "human_exception_rate": result.overall.human_exception_rate,
            "batch_summary_generated_at": result.generated_at,
        }
    )
    summary_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _batch_note(batch: BatchSummary) -> str:
    if batch.raw_signals == 0:
        return "无原始信号"
    if batch.quarantine_rate is not None and batch.quarantine_rate >= 0.3:
        return "隔离比例偏高，建议复核样本质量"
    if batch.human_exception_rate is not None and batch.human_exception_rate > 0.4:
        return "人工异常比例偏高，建议调校语义合并阈值"
    if batch.singleton_rate is not None and batch.singleton_rate > 0.75:
        return "主题仍偏分散"
    if batch.total_reviewed_groups > 0:
        return "已有 AI 或人工确认需求组"
    return "待继续审核"


def _percent(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.1f}%"


def _targeted_expansion_lines() -> list[str]:
    """Append Stage 3.3 Targeted Expansion summary if expansion summary exists."""
    import json
    summary_path = Path("data/processed/targeted_expansion_run_summary.json")
    if not summary_path.exists():
        return []
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except Exception:
        return []

    delta_path = Path("data/processed/truth_score_deltas.jsonl")
    improved = 0
    new_strong = 0
    new_proceed = 0
    if delta_path.exists():
        for line in delta_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                before = d.get("before_truth_score")
                after = d.get("after_truth_score")
                if before is not None and after is not None and after > before:
                    improved += 1
                if d.get("after_truth_level") == "strong":
                    new_strong += 1
                if d.get("after_next_action") == "proceed_to_fit_scoring":
                    new_proceed += 1
            except Exception:
                continue

    return [
        "",
        "## Stage 3.3: Targeted Evidence Expansion",
        "",
        f"- targeted_template_rows: {summary.get('template_rows', 0)}",
        f"- targeted_filled_signals: {summary.get('filled_signals', 0)}",
        f"- targeted_valid_signals: {summary.get('valid_signals', 0)}",
        f"- targeted_invalid_signals: {summary.get('invalid_signals', 0)}",
        f"- combined_input_rows: {summary.get('combined_input_rows', 0)}",
        f"- truth_score_improved_candidates: {improved}",
        f"- new_strong_candidates: {new_strong}",
        f"- new_proceed_to_fit_scoring: {new_proceed}",
        "",
    ]




def _stage35_lines() -> list[str]:
    """Stage 3.5 batch summary block."""
    from demand_radar.stage35.stage35_store import load_run_summary, load_gate_result
    summary = load_run_summary()
    gate = load_gate_result()
    if summary is None:
        return ["## Stage 3.5 Targeted Evidence Expansion", "", "Not run yet.", ""]
    sm = summary.model_dump()
    gs = gate.status if gate else "not_run"
    lines = [
        "## Stage 3.5 Targeted Evidence Expansion",
        "",
        f"- stage35_snapshot_status: {sm.get('lineage_baseline_quality', 'N/A')}",
        f"- stage35_selected_candidates: {sm.get('selected_candidates', 0)}",
        f"- stage35_template_rows: {sm.get('template_rows', 0)}",
        f"- stage35_valid_signals: {sm.get('valid_signals', 0)}",
        f"- stage35_combined_rows: {sm.get('combined_rows', 0)}",
        f"- stage35_attribution_rate: {sm.get('attribution_rate', 'N/A')}",
        f"- stage35_stable_delta_improved: {sm.get('stable_delta_improved', 'N/A')}",
        f"- stage35_stage4_gate_status: {gs}",
        "",
    ]
    return lines

def _lineage_lines() -> list[str]:
    """Append Stage 3.4 Lineage summary if lineage data exists."""
    import json
    from collections import Counter
    lineage_path = Path("data/processed/candidate_lineage.jsonl")
    if not lineage_path.exists():
        return []
    lineages = []
    for line in lineage_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            lineages.append(json.loads(line))
        except Exception:
            continue
    if not lineages:
        return []

    sc = Counter(l.get("match_strength", "") for l in lineages)
    drift_count = sum(1 for l in lineages if l.get("drift_flags"))

    attr_path = Path("data/processed/targeted_evidence_attribution.jsonl")
    attr_rate = "N/A"
    if attr_path.exists():
        attrs = []
        for line in attr_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    attrs.append(json.loads(line))
                except Exception:
                    pass
        if attrs:
            attributed = sum(1 for a in attrs if a.get("attribution_status") in
                             ("attributed_to_expected_group", "attributed_to_related_group"))
            attr_rate = f"{attributed/len(attrs):.1%}"

    delta_path = Path("data/processed/stable_truth_score_delta.jsonl")
    stable_improved = 0
    stable_proceed = 0
    if delta_path.exists():
        for line in delta_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                d = json.loads(line)
                if d.get("stable_delta") and d["stable_delta"] > 0:
                    stable_improved += 1
                if d.get("recommended_next_action") == "proceed_to_fit_scoring":
                    stable_proceed += 1
            except Exception:
                pass

    return [
        "",
        "## Stage 3.4: Candidate Lineage & Evidence Attribution",
        "",
        f"- candidate_lineages: {len(lineages)}",
        f"- strong_lineage_matches: {sc.get('strong', 0)}",
        f"- weak_lineage_matches: {sc.get('weak', 0)}",
        f"- lineage_drift_flags: {drift_count}",
        f"- targeted_attribution_rate: {attr_rate}",
        f"- stable_delta_improved: {stable_improved}",
        f"- stable_proceed_to_fit_scoring: {stable_proceed}",
        "",
    ]



def _real_evidence_lines() -> list[str]:
    """Stage R1 section for batch summary report."""
    import json
    from pathlib import Path

    items_path = Path("data/processed/real_evidence_items.jsonl")
    val_path = Path("data/processed/real_evidence_validation.jsonl")
    reviews_path = Path("data/processed/real_evidence_calibration_reviews.jsonl")

    def _load(p):
        if not p.exists():
            return []
        result = []
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    result.append(json.loads(line))
                except Exception:
                    pass
        return result

    items = _load(items_path)
    validations = _load(val_path)
    reviews = _load(reviews_path)

    valid_n = sum(1 for v in validations if v.get("status") == "valid")
    warn_n = sum(1 for v in validations if v.get("status") == "warning")
    inv_n = sum(1 for v in validations if v.get("status") == "invalid")

    url_n = sum(1 for i in items if i.get("source_url"))
    url_ratio = f"{url_n/len(items):.1%}" if items else "N/A"

    user_voice = sum(
        1 for i in items
        if i.get("source_type") in (
            "product_review", "community_discussion", "github_issue", "interview_note"
        )
    )
    paid_signal = sum(1 for i in items if i.get("paid_alternative") or i.get("budget_signal"))

    return [
        "",
        "## Stage R1: Real Evidence Pack & Calibration",
        "",
        f"- real_evidence_items: {len(items)}",
        f"- valid: {valid_n}",
        f"- warning: {warn_n}",
        f"- invalid: {inv_n}",
        f"- source_url_ratio: {url_ratio}",
        f"- user_voice_signals: {user_voice}",
        f"- paid_or_cost_signals: {paid_signal}",
        f"- calibration_reviews: {len(reviews)}",
        "",
    ]