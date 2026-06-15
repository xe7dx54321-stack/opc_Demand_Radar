"""Tests for LLM semantic merge judge runner (Stage 2.9)."""
from __future__ import annotations

import json
from pathlib import Path

from demand_radar.clustering.cluster_schema import DemandCluster
from demand_radar.clustering.cluster_store import write_demand_clusters
from demand_radar.clustering.merge_schema import ClusterMergeCandidate
from demand_radar.clustering.merge_store import write_merge_candidates
from demand_radar.semantic_merge.llm_client import FakeLLMClient
from demand_radar.semantic_merge.llm_judge_runner import (
    build_llm_ai_reviewed_cluster_groups,
    run_llm_semantic_merge_judge,
)
from demand_radar.semantic_merge.semantic_merge_store import load_semantic_merge_judgments


def _config_path(tmp_path: Path) -> Path:
    config = tmp_path / "semantic_merge_config.yaml"
    config.write_text(
        "semantic_merge:\n  mode: llm\n  thresholds:\n    auto_confirm:\n      confidence: 0.85\n"
        "    auto_reject:\n      confidence: 0.85\n    human_exception:\n      confidence: 0.85\n"
        "  batch:\n    max_candidates_per_run: 200\n    cache_enabled: false\n"
        "  require_reason_zh: true\n  require_evidence_alignment: false\n  require_workflow_judgment: false\n",
        encoding="utf-8",
    )
    return config


def _make_cluster(cluster_id: str, pain_ids: list[str]) -> DemandCluster:
    return DemandCluster(
        cluster_id=cluster_id, cluster_title_zh=f"需求主题{cluster_id}",
        cluster_summary_zh=f"需求主题{cluster_id}的摘要", personas=["investor"],
        domain_tags=["ai"], workflow_family="ai_research",
        related_pain_point_ids=pain_ids, evidence_count=len(pain_ids),
        source_count=1, representative_pain_descriptions=["信息分散"],
        representative_quotes=["引用示例"], current_workarounds=["人工表格"],
        cluster_confidence=0.60, cluster_method="rule_similarity_v1",
    )


def _make_candidate(ca: str, cb: str) -> ClusterMergeCandidate:
    return ClusterMergeCandidate(
        merge_candidate_id=f"mc_{ca}_{cb}", cluster_id_a=ca, cluster_id_b=cb,
        title_a=f"主题{ca}", title_b=f"主题{cb}",
        similarity_score=85.0, strength="strong",
        field_scores={"pain_description_similarity": 80.0},
        shared_personas=["investor"], shared_domain_tags=["ai"],
        shared_keywords=["信息分散"], batch_ids=["batch_a"],
        merge_reason_zh="两个主题痛点一致。",
    )


def _confirm_response() -> str:
    return json.dumps({
        "decision": "confirm_merge", "confidence": 0.92,
        "reason_zh": "两个主题核心痛点高度一致，建议合并。",
        "evidence_alignment_zh": "证据对齐良好",
        "workflow_judgment_zh": "属于同一工作流",
        "suggested_group_title_zh": "AI研究中遇到的信息分散问题",
        "suggested_group_summary_zh": "两个需求均涉及信息分散导致的人工整理负担。",
        "conflict_flags": [],
    })


def _reject_response() -> str:
    return json.dumps({
        "decision": "reject_merge", "confidence": 0.90,
        "reason_zh": "工作流和用户任务不同，不应合并。",
        "conflict_flags": ["different_workflow"],
    })


def _maybe_response() -> str:
    return json.dumps({
        "decision": "maybe_merge", "confidence": 0.55,
        "reason_zh": "证据不足以自动判断合并。",
        "conflict_flags": [],
    })


def _invalid_response() -> str:
    return "this is not json"


class TestRunLLMSemanticMergeJudge:
    def _write_fixtures(self, tmp_path: Path):
        clusters = [_make_cluster("ca001", ["p001"]), _make_cluster("cb001", ["p002"])]
        candidates = [_make_candidate("ca001", "cb001")]
        clusters_path = tmp_path / "clusters.jsonl"
        candidates_path = tmp_path / "candidates.jsonl"
        write_demand_clusters(clusters, clusters_path)
        write_merge_candidates(candidates, candidates_path)
        return clusters_path, candidates_path

    def test_confirm_judgment_auto_confirmed(self, tmp_path: Path):
        clusters_path, candidates_path = self._write_fixtures(tmp_path)
        client = FakeLLMClient(responses=[_confirm_response()])
        judgments_path = tmp_path / "llm_judgments.jsonl"
        exceptions_path = tmp_path / "llm_exceptions.jsonl"
        judgments = run_llm_semantic_merge_judge(
            candidates_path=candidates_path, clusters_path=clusters_path,
            judgments_path=judgments_path, exceptions_path=exceptions_path,
            config_path=_config_path(tmp_path), cache_path=tmp_path / "cache.jsonl",
            client=client,
        )
        assert len(judgments) == 1
        assert judgments[0].decision == "confirm_merge"
        assert judgments[0].auto_action == "auto_confirm"
        assert judgments[0].judge_mode == "llm"

    def test_reject_judgment_auto_rejected(self, tmp_path: Path):
        clusters_path, candidates_path = self._write_fixtures(tmp_path)
        client = FakeLLMClient(responses=[_reject_response()])
        judgments = run_llm_semantic_merge_judge(
            candidates_path=candidates_path, clusters_path=clusters_path,
            judgments_path=tmp_path / "j.jsonl", exceptions_path=tmp_path / "e.jsonl",
            config_path=_config_path(tmp_path), cache_path=tmp_path / "cache.jsonl",
            client=client,
        )
        assert judgments[0].decision == "reject_merge"
        assert judgments[0].auto_action == "auto_reject"

    def test_maybe_judgment_human_exception(self, tmp_path: Path):
        clusters_path, candidates_path = self._write_fixtures(tmp_path)
        client = FakeLLMClient(responses=[_maybe_response()])
        judgments = run_llm_semantic_merge_judge(
            candidates_path=candidates_path, clusters_path=clusters_path,
            judgments_path=tmp_path / "j.jsonl", exceptions_path=tmp_path / "e.jsonl",
            config_path=_config_path(tmp_path), cache_path=tmp_path / "cache.jsonl",
            client=client,
        )
        assert judgments[0].auto_action == "human_exception"

    def test_invalid_llm_output_becomes_human_exception(self, tmp_path: Path):
        clusters_path, candidates_path = self._write_fixtures(tmp_path)
        client = FakeLLMClient(responses=[_invalid_response()])
        judgments = run_llm_semantic_merge_judge(
            candidates_path=candidates_path, clusters_path=clusters_path,
            judgments_path=tmp_path / "j.jsonl", exceptions_path=tmp_path / "e.jsonl",
            config_path=_config_path(tmp_path), cache_path=tmp_path / "cache.jsonl",
            client=client,
        )
        assert judgments[0].auto_action == "human_exception"
        assert judgments[0].confidence == 0.0

    def test_cache_hit_skips_client_call(self, tmp_path: Path):
        clusters_path, candidates_path = self._write_fixtures(tmp_path)
        cache_path = tmp_path / "cache.jsonl"
        # Write a config with cache_enabled: true
        cache_config = tmp_path / "cache_cfg.yaml"
        cache_config.write_text(
            "semantic_merge:\n  mode: llm\n  thresholds:\n    auto_confirm:\n      confidence: 0.85\n"
            "    auto_reject:\n      confidence: 0.85\n    human_exception:\n      confidence: 0.85\n"
            "  batch:\n    max_candidates_per_run: 200\n    cache_enabled: true\n"
            "  require_reason_zh: true\n  require_evidence_alignment: false\n  require_workflow_judgment: false\n",
            encoding="utf-8",
        )
        client1 = FakeLLMClient(responses=[_confirm_response()])
        # First run: populates cache (cache_enabled: true)
        run_llm_semantic_merge_judge(
            candidates_path=candidates_path, clusters_path=clusters_path,
            judgments_path=tmp_path / "j1.jsonl", exceptions_path=tmp_path / "e1.jsonl",
            config_path=cache_config, cache_path=cache_path, client=client1,
        )
        assert client1.call_count == 1
        # Second run: should hit cache, not call client
        client2 = FakeLLMClient(responses=[_reject_response()])
        run_llm_semantic_merge_judge(
            candidates_path=candidates_path, clusters_path=clusters_path,
            judgments_path=tmp_path / "j2.jsonl", exceptions_path=tmp_path / "e2.jsonl",
            config_path=cache_config, cache_path=cache_path, client=client2,
        )
        assert client2.call_count == 0  # cache hit, no call

    def test_llm_groups_built_from_auto_confirmed(self, tmp_path: Path):
        clusters_path, candidates_path = self._write_fixtures(tmp_path)
        client = FakeLLMClient(responses=[_confirm_response()])
        judgments_path = tmp_path / "llm_j.jsonl"
        exceptions_path = tmp_path / "llm_e.jsonl"
        run_llm_semantic_merge_judge(
            candidates_path=candidates_path, clusters_path=clusters_path,
            judgments_path=judgments_path, exceptions_path=exceptions_path,
            config_path=_config_path(tmp_path), cache_path=tmp_path / "cache.jsonl",
            client=client,
        )
        groups = build_llm_ai_reviewed_cluster_groups(
            clusters_path=clusters_path,
            judgments_path=judgments_path,
            groups_path=tmp_path / "llm_groups.jsonl",
            invalid_groups_path=tmp_path / "invalid.jsonl",
        )
        assert len(groups) == 1
        assert "ca001" in groups[0].cluster_ids

    def test_outputs_separate_from_rule_based(self, tmp_path: Path):
        """LLM outputs go to llm_* paths, rule_based paths remain untouched."""
        clusters_path, candidates_path = self._write_fixtures(tmp_path)
        rule_path = tmp_path / "semantic_merge_judgments.jsonl"
        rule_path.write_text("", encoding="utf-8")  # empty baseline
        client = FakeLLMClient(responses=[_confirm_response()])
        llm_path = tmp_path / "llm_semantic_merge_judgments.jsonl"
        run_llm_semantic_merge_judge(
            candidates_path=candidates_path, clusters_path=clusters_path,
            judgments_path=llm_path, exceptions_path=tmp_path / "e.jsonl",
            config_path=_config_path(tmp_path), cache_path=tmp_path / "cache.jsonl",
            client=client,
        )
        # LLM judgments exist
        assert llm_path.exists() and llm_path.read_text(encoding="utf-8").strip()
        # Rule_based path untouched (still empty)
        assert rule_path.read_text(encoding="utf-8").strip() == ""

