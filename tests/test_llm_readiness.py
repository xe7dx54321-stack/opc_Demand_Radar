"""Tests for Stage 2.9 LLM readiness source logic."""
from __future__ import annotations

from pathlib import Path

from demand_radar.semantic_merge.llm_comparison_report import build_semantic_merge_comparison_report
from demand_radar.semantic_merge.semantic_merge_schema import SemanticMergeJudgment
from demand_radar.semantic_merge.semantic_merge_store import write_semantic_merge_judgments


def _make_confirm_judgment(jid: str, cid: str, ca: str, cb: str) -> SemanticMergeJudgment:
    return SemanticMergeJudgment(
        judgment_id=jid, merge_candidate_id=cid, cluster_id_a=ca, cluster_id_b=cb,
        decision="confirm_merge", confidence=0.92,
        reason_zh="两个主题核心痛点高度一致，建议合并。",
        suggested_group_title_zh="合并需求组标题",
        suggested_group_summary_zh="合并需求组摘要内容说明",
        auto_action="auto_confirm", judge_mode="llm",
    )


def test_readiness_source_is_llm_when_llm_judgments_exist(tmp_path: Path):
    rule_j = tmp_path / "rule.jsonl"
    llm_j = tmp_path / "llm.jsonl"
    rule_j.write_text("", encoding="utf-8")
    write_semantic_merge_judgments(
        [_make_confirm_judgment("j001", "mc001", "ca001", "cb001")],
        llm_j,
    )
    for p in (tmp_path / "rg.jsonl", tmp_path / "lg.jsonl", tmp_path / "re.jsonl", tmp_path / "le.jsonl"):
        p.write_text("", encoding="utf-8")
    summary = build_semantic_merge_comparison_report(
        rule_judgments_path=rule_j,
        llm_judgments_path=llm_j,
        rule_groups_path=tmp_path / "rg.jsonl",
        llm_groups_path=tmp_path / "lg.jsonl",
        rule_exceptions_path=tmp_path / "re.jsonl",
        llm_exceptions_path=tmp_path / "le.jsonl",
        report_path=tmp_path / "report.md",
        run_summary_path=tmp_path / "summary.json",
    )
    assert summary.readiness_source == "llm"
    assert summary.llm_judgments == 1


def test_readiness_source_is_rule_based_when_no_llm_judgments(tmp_path: Path):
    for p_name in ("rule.jsonl", "llm.jsonl", "rg.jsonl", "lg.jsonl", "re.jsonl", "le.jsonl"):
        (tmp_path / p_name).write_text("", encoding="utf-8")
    summary = build_semantic_merge_comparison_report(
        rule_judgments_path=tmp_path / "rule.jsonl",
        llm_judgments_path=tmp_path / "llm.jsonl",
        rule_groups_path=tmp_path / "rg.jsonl",
        llm_groups_path=tmp_path / "lg.jsonl",
        rule_exceptions_path=tmp_path / "re.jsonl",
        llm_exceptions_path=tmp_path / "le.jsonl",
        report_path=tmp_path / "report.md",
        run_summary_path=tmp_path / "summary.json",
    )
    assert summary.readiness_source == "rule_based"
    assert summary.llm_judgments == 0
