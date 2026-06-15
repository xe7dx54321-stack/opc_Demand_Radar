"""Tests for Stage 3 readiness with AI + human reviewed groups (Stage 2.8)."""
from __future__ import annotations

from pathlib import Path

from demand_radar.batch.batch_summary import build_batch_summary
from demand_radar.clustering.cluster_schema import DemandCluster
from demand_radar.clustering.cluster_store import write_demand_clusters
from demand_radar.clustering.merge_schema import ClusterMergeCandidate
from demand_radar.clustering.merge_store import write_merge_candidates
from demand_radar.semantic_merge.semantic_merge_schema import (
    AIReviewedClusterGroup,
    SemanticMergeJudgment,
)
from demand_radar.semantic_merge.semantic_merge_store import (
    write_ai_reviewed_cluster_groups,
    write_semantic_merge_judgments,
)
from demand_radar.state.raw_store import utc_now_iso, write_jsonl


def _empty_path(tmp_path: Path, name: str) -> Path:
    path = tmp_path / name
    path.write_text("", encoding="utf-8")
    return path


def _write_minimal_paths(tmp_path: Path) -> dict[str, Path]:
    return {
        "raw": _empty_path(tmp_path, "raw.jsonl"),
        "normalized": _empty_path(tmp_path, "normalized.jsonl"),
        "pain": _empty_path(tmp_path, "pain.jsonl"),
        "quarantine": _empty_path(tmp_path, "quarantine.jsonl"),
        "calibration_reviews": _empty_path(tmp_path, "cal_reviews.jsonl"),
        "clusters": _empty_path(tmp_path, "clusters.jsonl"),
        "cluster_reviews": _empty_path(tmp_path, "cluster_reviews.jsonl"),
        "merge_candidates": _empty_path(tmp_path, "candidates.jsonl"),
        "merge_reviews": _empty_path(tmp_path, "merge_reviews.jsonl"),
        "reviewed_groups": _empty_path(tmp_path, "reviewed_groups.jsonl"),
        "semantic_judgments": _empty_path(tmp_path, "judgments.jsonl"),
        "ai_reviewed_groups": _empty_path(tmp_path, "ai_groups.jsonl"),
        "human_exceptions": _empty_path(tmp_path, "exceptions.jsonl"),
    }


def _make_ai_group(group_id: str, cluster_ids: list[str], pain_ids: list[str]) -> AIReviewedClusterGroup:
    return AIReviewedClusterGroup(
        group_id=group_id,
        group_title_zh=f"测试需求组{group_id}",
        group_summary_zh=f"测试需求组{group_id}的摘要说明内容",
        cluster_ids=cluster_ids,
        related_pain_point_ids=pain_ids,
        evidence_count=len(pain_ids),
        source_count=1,
        created_from_judgment_ids=[f"j_{group_id}"],
    )


def test_effective_reviewed_groups_uses_ai_groups(tmp_path: Path):
    paths = _write_minimal_paths(tmp_path)
    groups = [_make_ai_group(f"g{i:03d}", [f"ca{i:03d}", f"cb{i:03d}"], [f"p{i:03d}a", f"p{i:03d}b"]) for i in range(6)]
    write_ai_reviewed_cluster_groups(groups, paths["ai_reviewed_groups"])

    result = build_batch_summary(
        raw_path=paths["raw"],
        normalized_path=paths["normalized"],
        pain_points_path=paths["pain"],
        quarantine_path=paths["quarantine"],
        calibration_reviews_path=paths["calibration_reviews"],
        clusters_path=paths["clusters"],
        cluster_reviews_path=paths["cluster_reviews"],
        merge_candidates_path=paths["merge_candidates"],
        merge_reviews_path=paths["merge_reviews"],
        reviewed_groups_path=paths["reviewed_groups"],
        semantic_judgments_path=paths["semantic_judgments"],
        ai_reviewed_groups_path=paths["ai_reviewed_groups"],
        human_exceptions_path=paths["human_exceptions"],
    )
    assert result.overall.ai_reviewed_groups == 6
    assert result.overall.total_reviewed_groups >= 6


def test_stage3_readiness_uses_effective_groups(tmp_path: Path):
    paths = _write_minimal_paths(tmp_path)
    groups = [_make_ai_group(f"g{i:03d}", [f"ca{i:03d}", f"cb{i:03d}"], [f"p{i:03d}a", f"p{i:03d}b"]) for i in range(5)]
    write_ai_reviewed_cluster_groups(groups, paths["ai_reviewed_groups"])

    result = build_batch_summary(
        raw_path=paths["raw"],
        normalized_path=paths["normalized"],
        pain_points_path=paths["pain"],
        quarantine_path=paths["quarantine"],
        calibration_reviews_path=paths["calibration_reviews"],
        clusters_path=paths["clusters"],
        cluster_reviews_path=paths["cluster_reviews"],
        merge_candidates_path=paths["merge_candidates"],
        merge_reviews_path=paths["merge_reviews"],
        reviewed_groups_path=paths["reviewed_groups"],
        semantic_judgments_path=paths["semantic_judgments"],
        ai_reviewed_groups_path=paths["ai_reviewed_groups"],
        human_exceptions_path=paths["human_exceptions"],
    )
    assert result.readiness.auto_confirmed_groups_ok is True
    assert result.readiness.group_volume_ok is True


def test_stage3_readiness_fails_without_groups(tmp_path: Path):
    paths = _write_minimal_paths(tmp_path)
    result = build_batch_summary(
        raw_path=paths["raw"],
        normalized_path=paths["normalized"],
        pain_points_path=paths["pain"],
        quarantine_path=paths["quarantine"],
        calibration_reviews_path=paths["calibration_reviews"],
        clusters_path=paths["clusters"],
        cluster_reviews_path=paths["cluster_reviews"],
        merge_candidates_path=paths["merge_candidates"],
        merge_reviews_path=paths["merge_reviews"],
        reviewed_groups_path=paths["reviewed_groups"],
        semantic_judgments_path=paths["semantic_judgments"],
        ai_reviewed_groups_path=paths["ai_reviewed_groups"],
        human_exceptions_path=paths["human_exceptions"],
    )
    assert result.readiness.group_volume_ok is False
    assert result.readiness.auto_confirmed_groups_ok is False


def test_exception_rate_ok_with_low_exception_rate(tmp_path: Path):
    paths = _write_minimal_paths(tmp_path)
    # 8 auto_reject + 2 human_exception = 20% exception rate
    reject_judgments = [
        SemanticMergeJudgment(
            judgment_id=f"j{i:03d}",
            merge_candidate_id=f"mc{i:03d}",
            cluster_id_a=f"ca{i:03d}",
            cluster_id_b=f"cb{i:03d}",
            decision="reject_merge",
            confidence=0.88,
            reason_zh="工作流完全不同，不应合并。",
            auto_action="auto_reject",
            judge_mode="rule_based_stub",
        )
        for i in range(8)
    ]
    exception_judgments = [
        SemanticMergeJudgment(
            judgment_id=f"j{i:03d}",
            merge_candidate_id=f"mc{i:03d}",
            cluster_id_a=f"ca{i:03d}",
            cluster_id_b=f"cb{i:03d}",
            decision="maybe_merge",
            confidence=0.55,
            reason_zh="证据不足，需要人工审核。",
            auto_action="human_exception",
            judge_mode="rule_based_stub",
        )
        for i in range(8, 10)
    ]
    write_semantic_merge_judgments(reject_judgments + exception_judgments, paths["semantic_judgments"])
    result = build_batch_summary(
        raw_path=paths["raw"],
        normalized_path=paths["normalized"],
        pain_points_path=paths["pain"],
        quarantine_path=paths["quarantine"],
        calibration_reviews_path=paths["calibration_reviews"],
        clusters_path=paths["clusters"],
        cluster_reviews_path=paths["cluster_reviews"],
        merge_candidates_path=paths["merge_candidates"],
        merge_reviews_path=paths["merge_reviews"],
        reviewed_groups_path=paths["reviewed_groups"],
        semantic_judgments_path=paths["semantic_judgments"],
        ai_reviewed_groups_path=paths["ai_reviewed_groups"],
        human_exceptions_path=paths["human_exceptions"],
    )
    assert result.overall.semantic_judgments == 10

