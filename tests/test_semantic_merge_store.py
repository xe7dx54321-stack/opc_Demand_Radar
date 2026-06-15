"""Tests for semantic merge store and AI reviewed group building."""
from __future__ import annotations

from pathlib import Path

from demand_radar.clustering.cluster_schema import DemandCluster
from demand_radar.clustering.cluster_store import write_demand_clusters
from demand_radar.clustering.merge_schema import ClusterMergeCandidate
from demand_radar.clustering.merge_store import write_merge_candidates
from demand_radar.semantic_merge.semantic_merge_judge import run_semantic_merge_judge
from demand_radar.semantic_merge.semantic_merge_store import (
    build_ai_reviewed_cluster_groups,
    build_human_exception_queue,
    load_ai_reviewed_cluster_groups,
    load_human_exception_items,
    load_semantic_merge_judgments,
    write_semantic_merge_judgments,
)
from demand_radar.semantic_merge.semantic_merge_schema import SemanticMergeJudgment
from demand_radar.state.raw_store import next_ids, utc_now_iso


def _make_cluster(cluster_id: str, pain_ids: list[str], workflow: str = "ai_investment_research") -> DemandCluster:
    return DemandCluster(
        cluster_id=cluster_id,
        cluster_title_zh=f"需求主题{cluster_id}",
        cluster_summary_zh=f"需求主题{cluster_id}的摘要说明内容",
        personas=["investor"],
        domain_tags=["ai_investment_research"],
        workflow_family=workflow,
        related_pain_point_ids=pain_ids,
        evidence_count=len(pain_ids),
        source_count=1,
        representative_pain_descriptions=["信息分散，人工整理低效"],
        representative_quotes=["原始引用内容"],
        current_workarounds=["人工表格"],
        cluster_confidence=0.60,
        cluster_method="rule_similarity_v1",
    )


def _make_candidate(cid_a: str, cid_b: str, candidate_id: str) -> ClusterMergeCandidate:
    return ClusterMergeCandidate(
        merge_candidate_id=candidate_id,
        cluster_id_a=cid_a,
        cluster_id_b=cid_b,
        title_a=f"主题{cid_a}",
        title_b=f"主题{cid_b}",
        similarity_score=88.0,
        strength="strong",
        field_scores={"pain_description_similarity": 82.0, "summary_similarity": 78.0},
        shared_personas=["investor"],
        shared_domain_tags=["ai_investment_research"],
        shared_keywords=["信息分散"],
        batch_ids=["batch_a"],
        merge_reason_zh="两个主题痛点高度一致，建议合并。",
    )


def _make_auto_confirm_judgment(
    judgment_id: str, candidate_id: str, cluster_id_a: str, cluster_id_b: str
) -> SemanticMergeJudgment:
    return SemanticMergeJudgment(
        judgment_id=judgment_id,
        merge_candidate_id=candidate_id,
        cluster_id_a=cluster_id_a,
        cluster_id_b=cluster_id_b,
        decision="confirm_merge",
        confidence=0.90,
        reason_zh="两个主题核心痛点高度一致，建议合并。",
        suggested_group_title_zh="用户在工作流中遇到的信息分散问题",
        suggested_group_summary_zh="两个需求均涉及信息分散导致的人工整理负担。",
        auto_action="auto_confirm",
        judge_mode="rule_based_stub",
    )


def _make_human_exception_judgment(
    judgment_id: str, candidate_id: str, cluster_id_a: str, cluster_id_b: str
) -> SemanticMergeJudgment:
    return SemanticMergeJudgment(
        judgment_id=judgment_id,
        merge_candidate_id=candidate_id,
        cluster_id_a=cluster_id_a,
        cluster_id_b=cluster_id_b,
        decision="maybe_merge",
        confidence=0.55,
        reason_zh="证据不足以自动判断，需要人工裁决。",
        auto_action="human_exception",
        judge_mode="rule_based_stub",
    )


class TestWriteAndLoadJudgments:
    def test_write_and_load_roundtrip(self, tmp_path: Path):
        path = tmp_path / "judgments.jsonl"
        j1 = _make_auto_confirm_judgment("j001", "mc001", "ca001", "cb001")
        write_semantic_merge_judgments([j1], path)
        loaded = load_semantic_merge_judgments(path)
        assert len(loaded) == 1
        assert loaded[0].judgment_id == "j001"
        assert loaded[0].auto_action == "auto_confirm"


class TestBuildHumanExceptionQueue:
    def test_only_exception_judgments_enter_queue(self):
        j_confirm = _make_auto_confirm_judgment("j001", "mc001", "ca001", "cb001")
        j_exception = _make_human_exception_judgment("j002", "mc002", "ca002", "cb002")
        items = build_human_exception_queue([j_confirm, j_exception])
        assert len(items) == 1
        assert items[0].judgment_id == "j002"

    def test_auto_reject_does_not_enter_queue(self):
        j_reject = SemanticMergeJudgment(
            judgment_id="j003",
            merge_candidate_id="mc003",
            cluster_id_a="ca003",
            cluster_id_b="cb003",
            decision="reject_merge",
            confidence=0.88,
            reason_zh="工作流完全不同，不应合并。",
            auto_action="auto_reject",
            judge_mode="rule_based_stub",
            conflict_flags=[],
        )
        items = build_human_exception_queue([j_reject])
        assert len(items) == 0


class TestBuildAIReviewedClusterGroups:
    def test_auto_confirm_builds_group(self, tmp_path: Path):
        clusters = [
            _make_cluster("ca001", ["p001"]),
            _make_cluster("cb001", ["p002"]),
        ]
        clusters_path = tmp_path / "demand_clusters.jsonl"
        write_demand_clusters(clusters, clusters_path)

        j = _make_auto_confirm_judgment("j001", "mc001", "ca001", "cb001")
        judgments_path = tmp_path / "judgments.jsonl"
        write_semantic_merge_judgments([j], judgments_path)

        groups_path = tmp_path / "groups.jsonl"
        invalid_path = tmp_path / "invalid.jsonl"
        groups = build_ai_reviewed_cluster_groups(
            clusters_path=clusters_path,
            judgments_path=judgments_path,
            groups_path=groups_path,
            invalid_groups_path=invalid_path,
        )
        assert len(groups) == 1
        group = groups[0]
        assert "ca001" in group.cluster_ids
        assert "cb001" in group.cluster_ids
        assert "j001" in group.created_from_judgment_ids
        assert group.evidence_count >= 2

    def test_auto_reject_does_not_build_group(self, tmp_path: Path):
        clusters = [
            _make_cluster("ca001", ["p001"]),
            _make_cluster("cb001", ["p002"]),
        ]
        clusters_path = tmp_path / "demand_clusters.jsonl"
        write_demand_clusters(clusters, clusters_path)

        j = SemanticMergeJudgment(
            judgment_id="j001",
            merge_candidate_id="mc001",
            cluster_id_a="ca001",
            cluster_id_b="cb001",
            decision="reject_merge",
            confidence=0.88,
            reason_zh="工作流完全不同，不应合并。",
            auto_action="auto_reject",
            judge_mode="rule_based_stub",
            conflict_flags=["different_workflow"],
        )
        judgments_path = tmp_path / "judgments.jsonl"
        write_semantic_merge_judgments([j], judgments_path)

        groups_path = tmp_path / "groups.jsonl"
        invalid_path = tmp_path / "invalid.jsonl"
        groups = build_ai_reviewed_cluster_groups(
            clusters_path=clusters_path,
            judgments_path=judgments_path,
            groups_path=groups_path,
            invalid_groups_path=invalid_path,
        )
        assert len(groups) == 0

    def test_connected_components_abc(self, tmp_path: Path):
        """A+B confirm AND B+C confirm => single group [A, B, C]."""
        clusters = [
            _make_cluster("ca001", ["p001"]),
            _make_cluster("cb001", ["p002"]),
            _make_cluster("cc001", ["p003"]),
        ]
        clusters_path = tmp_path / "demand_clusters.jsonl"
        write_demand_clusters(clusters, clusters_path)

        j1 = _make_auto_confirm_judgment("j001", "mc001", "ca001", "cb001")
        j2 = _make_auto_confirm_judgment("j002", "mc002", "cb001", "cc001")
        judgments_path = tmp_path / "judgments.jsonl"
        write_semantic_merge_judgments([j1, j2], judgments_path)

        groups_path = tmp_path / "groups.jsonl"
        invalid_path = tmp_path / "invalid.jsonl"
        groups = build_ai_reviewed_cluster_groups(
            clusters_path=clusters_path,
            judgments_path=judgments_path,
            groups_path=groups_path,
            invalid_groups_path=invalid_path,
        )
        assert len(groups) == 1
        assert set(groups[0].cluster_ids) == {"ca001", "cb001", "cc001"}

    def test_no_confirm_no_group(self, tmp_path: Path):
        clusters = [_make_cluster("ca001", ["p001"]), _make_cluster("cb001", ["p002"])]
        clusters_path = tmp_path / "demand_clusters.jsonl"
        write_demand_clusters(clusters, clusters_path)

        judgments_path = tmp_path / "judgments.jsonl"
        judgments_path.write_text("", encoding="utf-8")

        groups_path = tmp_path / "groups.jsonl"
        invalid_path = tmp_path / "invalid.jsonl"
        groups = build_ai_reviewed_cluster_groups(
            clusters_path=clusters_path,
            judgments_path=judgments_path,
            groups_path=groups_path,
            invalid_groups_path=invalid_path,
        )
        assert groups == []


