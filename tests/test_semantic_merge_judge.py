"""Tests for semantic merge judge implementations."""
from __future__ import annotations

from demand_radar.clustering.cluster_schema import DemandCluster
from demand_radar.clustering.merge_schema import ClusterMergeCandidate
from demand_radar.semantic_merge.semantic_merge_judge import (
    FakeLLMJudge,
    LLMSemanticMergeJudgeStub,
    RuleBasedSemanticMergeJudge,
    _make_judge,
)
from demand_radar.state.raw_store import utc_now_iso


def _make_cluster(
    cluster_id: str,
    title: str = "需求主题标题",
    summary: str = "需求主题摘要说明",
    persona: str = "investor",
    domain: str = "ai_investment_research",
    workflow: str | None = "ai_investment_research",
    pain: str = "信息分散，人工整理低效",
) -> DemandCluster:
    return DemandCluster(
        cluster_id=cluster_id,
        cluster_title_zh=title,
        cluster_summary_zh=summary,
        personas=[persona],
        domain_tags=[domain],
        workflow_family=workflow,
        related_pain_point_ids=[f"pain_{cluster_id}"],
        evidence_count=1,
        source_count=1,
        representative_pain_descriptions=[pain],
        representative_quotes=["原始引用说明"],
        current_workarounds=["人工表格"],
        cluster_confidence=0.60,
        cluster_method="rule_similarity_v1",
    )


def _make_candidate(
    cluster_id_a: str = "ca001",
    cluster_id_b: str = "cb001",
    similarity_score: float = 85.0,
    field_scores: dict | None = None,
    shared_personas: list[str] | None = None,
    shared_domain_tags: list[str] | None = None,
) -> ClusterMergeCandidate:
    if field_scores is None:
        field_scores = {"pain_description_similarity": 80.0, "summary_similarity": 75.0}
    return ClusterMergeCandidate(
        merge_candidate_id="mc001",
        cluster_id_a=cluster_id_a,
        cluster_id_b=cluster_id_b,
        title_a="主题甲",
        title_b="主题乙",
        similarity_score=similarity_score,
        strength="strong",
        field_scores=field_scores or {},
        shared_personas=shared_personas or ["investor"],
        shared_domain_tags=shared_domain_tags or ["ai_investment_research"],
        shared_keywords=["信息分散", "人工整理"],
        batch_ids=["batch_a"],
        merge_reason_zh="两个主题的核心痛点高度一致。",
    )


_DEFAULT_CTX = {"config": {}, "judgment_id": "j001"}


# ------------------------------------------------------------------
# RuleBasedSemanticMergeJudge
# ------------------------------------------------------------------

class TestRuleBasedJudge:
    def test_rule_based_does_not_call_external_apis(self):
        """No network calls - runs fully offline."""
        judge = RuleBasedSemanticMergeJudge()
        ca = _make_cluster("ca001")
        cb = _make_cluster("cb001")
        candidate = _make_candidate()
        judgment = judge.judge(candidate, ca, cb, _DEFAULT_CTX)
        assert judgment.judge_mode == "rule_based_stub"

    def test_high_similarity_confirms_merge(self):
        judge = RuleBasedSemanticMergeJudge()
        ca = _make_cluster("ca001", workflow="ai_investment_research")
        cb = _make_cluster("cb001", workflow="ai_investment_research")
        candidate = _make_candidate(
            similarity_score=88.0,
            field_scores={"pain_description_similarity": 82.0, "summary_similarity": 78.0},
            shared_personas=["investor"],
        )
        judgment = judge.judge(candidate, ca, cb, _DEFAULT_CTX)
        assert judgment.decision == "confirm_merge"
        assert judgment.auto_action == "auto_confirm"
        assert judgment.confidence >= 0.85

    def test_low_similarity_rejects_merge(self):
        judge = RuleBasedSemanticMergeJudge()
        ca = _make_cluster("ca001", persona="developer", domain="developer_workflow", workflow="developer_workflow")
        cb = _make_cluster("cb001", persona="investor", domain="ai_investment_research", workflow="ai_investment_research")
        candidate = _make_candidate(
            similarity_score=50.0,
            field_scores={"pain_description_similarity": 40.0, "summary_similarity": 35.0},
            shared_personas=[],
            shared_domain_tags=[],
        )
        judgment = judge.judge(candidate, ca, cb, _DEFAULT_CTX)
        assert judgment.decision == "reject_merge"

    def test_mid_similarity_becomes_maybe(self):
        judge = RuleBasedSemanticMergeJudge()
        ca = _make_cluster("ca001")
        cb = _make_cluster("cb001", workflow="content_production")
        candidate = _make_candidate(
            similarity_score=70.0,
            field_scores={"pain_description_similarity": 65.0, "summary_similarity": 60.0},
            shared_personas=[],
        )
        judgment = judge.judge(candidate, ca, cb, _DEFAULT_CTX)
        assert judgment.decision == "maybe_merge"
        assert judgment.auto_action == "human_exception"

    def test_confirm_merge_populates_title_and_summary(self):
        judge = RuleBasedSemanticMergeJudge()
        ca = _make_cluster("ca001", workflow="ai_investment_research")
        cb = _make_cluster("cb001", workflow="ai_investment_research")
        candidate = _make_candidate(
            similarity_score=88.0,
            field_scores={"pain_description_similarity": 82.0, "summary_similarity": 78.0},
        )
        judgment = judge.judge(candidate, ca, cb, _DEFAULT_CTX)
        if judgment.decision == "confirm_merge":
            assert judgment.suggested_group_title_zh
            assert judgment.suggested_group_summary_zh

    def test_reason_is_chinese(self):
        judge = RuleBasedSemanticMergeJudge()
        ca = _make_cluster("ca001")
        cb = _make_cluster("cb001")
        candidate = _make_candidate()
        judgment = judge.judge(candidate, ca, cb, _DEFAULT_CTX)
        assert any("\u4e00" <= char <= "\u9fff" for char in judgment.reason_zh)


# ------------------------------------------------------------------
# FakeLLMJudge
# ------------------------------------------------------------------

class TestFakeLLMJudge:
    def test_fake_judge_does_not_call_network(self):
        judge = FakeLLMJudge(responses=[{
            "decision": "confirm_merge",
            "confidence": 0.92,
            "reason_zh": "测试判断理由内容",
            "suggested_group_title_zh": "测试合并后标题",
            "suggested_group_summary_zh": "测试合并后摘要内容",
            "conflict_flags": [],
        }])
        ca = _make_cluster("ca001")
        cb = _make_cluster("cb001")
        candidate = _make_candidate()
        judgment = judge.judge(candidate, ca, cb, _DEFAULT_CTX)
        assert judgment.judge_mode == "llm"
        assert judgment.decision == "confirm_merge"
        assert judgment.auto_action == "auto_confirm"

    def test_fake_judge_auto_reject(self):
        judge = FakeLLMJudge(responses=[{
            "decision": "reject_merge",
            "confidence": 0.90,
            "reason_zh": "工作流完全不同，不应合并。",
            "conflict_flags": ["different_workflow"],
        }])
        ca = _make_cluster("ca001")
        cb = _make_cluster("cb001")
        candidate = _make_candidate()
        judgment = judge.judge(candidate, ca, cb, _DEFAULT_CTX)
        assert judgment.decision == "reject_merge"
        assert judgment.auto_action == "auto_reject"

    def test_fake_judge_maybe_merge_becomes_exception(self):
        judge = FakeLLMJudge(responses=[{
            "decision": "maybe_merge",
            "confidence": 0.60,
            "reason_zh": "证据不足以自动判断合并。",
        }])
        ca = _make_cluster("ca001")
        cb = _make_cluster("cb001")
        candidate = _make_candidate()
        judgment = judge.judge(candidate, ca, cb, _DEFAULT_CTX)
        assert judgment.decision == "maybe_merge"
        assert judgment.auto_action == "human_exception"

    def test_fake_judge_invalid_decision_falls_back_to_maybe(self):
        judge = FakeLLMJudge(responses=[{
            "decision": "not_valid",
            "confidence": 0.90,
            "reason_zh": "理由内容",
        }])
        ca = _make_cluster("ca001")
        cb = _make_cluster("cb001")
        candidate = _make_candidate()
        judgment = judge.judge(candidate, ca, cb, _DEFAULT_CTX)
        assert judgment.decision == "maybe_merge"

    def test_fake_judge_with_severe_conflict_flag_blocks_auto_confirm(self):
        judge = FakeLLMJudge(responses=[{
            "decision": "confirm_merge",
            "confidence": 0.95,
            "reason_zh": "主题核心痛点相似，建议合并。",
            "suggested_group_title_zh": "合并标题",
            "suggested_group_summary_zh": "合并摘要内容",
            "conflict_flags": ["different_persona"],
        }])
        ca = _make_cluster("ca001")
        cb = _make_cluster("cb001")
        candidate = _make_candidate()
        judgment = judge.judge(candidate, ca, cb, _DEFAULT_CTX)
        assert judgment.auto_action == "human_exception"


# ------------------------------------------------------------------
# _make_judge factory
# ------------------------------------------------------------------

class TestMakeJudge:
    def test_default_mode_returns_rule_based(self, monkeypatch):
        monkeypatch.delenv("DEMAND_RADAR_LLM_BASE_URL", raising=False)
        monkeypatch.delenv("DEMAND_RADAR_LLM_API_KEY", raising=False)
        judge = _make_judge({"mode": "rule_based_stub"})
        assert isinstance(judge, RuleBasedSemanticMergeJudge)

    def test_llm_mode_without_env_returns_stub(self, monkeypatch):
        monkeypatch.delenv("DEMAND_RADAR_LLM_BASE_URL", raising=False)
        monkeypatch.delenv("DEMAND_RADAR_LLM_API_KEY", raising=False)
        judge = _make_judge({"mode": "llm", "llm": {"model": "gpt-4o", "base_url_env": "DEMAND_RADAR_LLM_BASE_URL", "api_key_env": "DEMAND_RADAR_LLM_API_KEY"}})
        assert isinstance(judge, LLMSemanticMergeJudgeStub)
