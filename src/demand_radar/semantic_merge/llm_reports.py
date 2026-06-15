"""LLM-specific output paths and report builders for Stage 2.9."""
from __future__ import annotations

from pathlib import Path

from demand_radar.semantic_merge.semantic_merge_report import (
    AIReviewedGroupsReportSummary,
    HumanExceptionReportSummary,
    SemanticMergeReportSummary,
    build_ai_reviewed_groups_report,
    build_human_exception_report,
    build_semantic_merge_report,
)


# Default LLM-specific paths
LLM_JUDGMENTS = "data/processed/llm_semantic_merge_judgments.jsonl"
LLM_EXCEPTIONS = "data/processed/llm_human_exception_queue.jsonl"
LLM_GROUPS = "data/processed/llm_ai_reviewed_cluster_groups.jsonl"
LLM_INVALID_GROUPS = "data/quarantine/invalid_llm_ai_reviewed_groups.jsonl"

LLM_JUDGMENT_REPORT = "outputs/llm_semantic_merge_judgment_report.md"
LLM_GROUPS_REPORT = "outputs/llm_ai_reviewed_cluster_groups_report.md"
LLM_EXCEPTIONS_REPORT = "outputs/llm_human_exception_queue_report.md"


def build_llm_semantic_merge_report(
    candidates_path: str | Path = "data/processed/cluster_merge_candidates.jsonl",
    judgments_path: str | Path = LLM_JUDGMENTS,
    exceptions_path: str | Path = LLM_EXCEPTIONS,
    report_path: str | Path = LLM_JUDGMENT_REPORT,
    summary_path: str | Path = "outputs/run_summary.json",
) -> SemanticMergeReportSummary:
    return build_semantic_merge_report(
        candidates_path=candidates_path,
        judgments_path=judgments_path,
        exceptions_path=exceptions_path,
        report_path=report_path,
        summary_path=summary_path,
    )


def build_llm_human_exception_report(
    exceptions_path: str | Path = LLM_EXCEPTIONS,
    report_path: str | Path = LLM_EXCEPTIONS_REPORT,
    summary_path: str | Path = "outputs/run_summary.json",
) -> HumanExceptionReportSummary:
    return build_human_exception_report(
        exceptions_path=exceptions_path,
        report_path=report_path,
        summary_path=summary_path,
    )


def build_llm_ai_reviewed_groups_report(
    groups_path: str | Path = LLM_GROUPS,
    report_path: str | Path = LLM_GROUPS_REPORT,
    summary_path: str | Path = "outputs/run_summary.json",
) -> AIReviewedGroupsReportSummary:
    return build_ai_reviewed_groups_report(
        groups_path=groups_path,
        report_path=report_path,
        summary_path=summary_path,
    )
