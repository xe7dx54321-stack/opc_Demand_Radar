"""Batch summary report generation for Stage 2.6."""

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
        f"- Reviewed groups: {overall.reviewed_groups}",
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
        f"- Reviewed groups: {batch.reviewed_groups}",
        "",
        "Extraction Quality:",
        f"- Good: {batch.good_extractions}",
        f"- Weak: {batch.weak_extractions}",
        f"- False positive: {batch.false_positives}",
        f"- Bad quote: {batch.bad_quotes}",
        f"- Should quarantine: {batch.should_quarantine}",
        "",
        "Observations:",
        f"- 抽取产出率：{_percent(batch.extraction_yield)}；单证据主题比例：{_percent(batch.singleton_rate)}；合并建议密度：{_percent(batch.merge_candidate_rate)}。",
        "",
    ]


def _quality_matrix_lines(batches: list[BatchSummary]) -> list[str]:
    lines = [
        "## Quality Matrix",
        "",
        "| Batch | Raw | Pain Points | Quarantine Rate | Clusters | Singleton Rate | Merge Candidates | Reviewed Groups | Notes |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for batch in batches:
        lines.append(
            "| "
            f"{batch.batch_id} | {batch.raw_signals} | {batch.pain_points} | "
            f"{_percent(batch.quarantine_rate)} | {batch.demand_clusters} | "
            f"{_percent(batch.singleton_rate)} | {batch.merge_candidates} | "
            f"{batch.reviewed_groups} | {_batch_note(batch)} |"
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
        f"- Are clusters sufficiently converging? {'yes' if readiness.clustering_convergence_ok else 'no'}",
        f"- Are reviewed groups enough? {'yes' if readiness.group_volume_ok else 'no'}",
        f"- ready_for_truth_scoring: {readiness.ready_for_truth_scoring}",
        f"- Recommendation: {readiness.recommendation}",
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
                "reviewed_groups",
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
                    "reviewed_groups": batch.reviewed_groups,
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
            "batch_summary_generated_at": result.generated_at,
        }
    )
    summary_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _batch_note(batch: BatchSummary) -> str:
    if batch.raw_signals == 0:
        return "无原始信号"
    if batch.quarantine_rate is not None and batch.quarantine_rate >= 0.3:
        return "隔离比例偏高，建议复核样本质量"
    if batch.singleton_rate is not None and batch.singleton_rate > 0.75:
        return "主题仍偏分散"
    if batch.reviewed_groups > 0:
        return "已有人工确认需求组"
    return "待继续审核"


def _percent(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.1f}%"
