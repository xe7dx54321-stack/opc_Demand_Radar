"""Tests for LLM semantic merge comparison report (Stage 2.9)."""
from __future__ import annotations

from pathlib import Path

from demand_radar.semantic_merge.llm_comparison_report import (
    ComparisonSummary,
    build_semantic_merge_comparison_report,
)
from demand_radar.semantic_merge.semantic_merge_schema import SemanticMergeJudgment
from demand_radar.semantic_merge.semantic_merge_store import (
    write_ai_reviewed_cluster_groups,
    write_semantic_merge_judgments,
    write_human_exception_items,
)
from demand_radar.semantic_merge.exception_queue import build_exception_item


def _make_judgment(jid: str, cid: str, decision: str, auto_action: str, ca: str, cb: str) -> SemanticMergeJudgment:
    return SemanticMergeJudgment(
        judgment_id=jid, merge_candidate_id=cid, cluster_id_a=ca, cluster_id_b=cb,
        decision=decision, confidence=0.90 if decision != "maybe_merge" else 0.55,
        reason_zh="测试判断理由（中文内容）",
        auto_action=auto_action, judge_mode="rule_based_stub",
    )


def _write_fixtures(tmp_path: Path):
    # rule_based: 5 auto_reject + 3 maybe/human_exception
    rule_judgments = [
        _make_judgment(f"rb_j{i:03d}", f"mc{i:03d}", "reject_merge", "auto_reject", f"ca{i:03d}", f"cb{i:03d}")
        for i in range(5)
    ] + [
        _make_judgment(f"rb_j{i:03d}", f"mc{i:03d}", "maybe_merge", "human_exception", f"ca{i:03d}", f"cb{i:03d}")
        for i in range(5, 8)
    ]
    # LLM: 6 auto_confirm + 2 auto_reject + 0 exception
    llm_judgments = [
        SemanticMergeJudgment(
            judgment_id=f"llm_j{i:03d}", merge_candidate_id=f"mc{i:03d}",
            cluster_id_a=f"ca{i:03d}", cluster_id_b=f"cb{i:03d}",
            decision="confirm_merge", confidence=0.92,
            reason_zh=f"需求主题{i}核心痛点高度一致，建议合并。",
            suggested_group_title_zh=f"需求组{i}合并标题",
            suggested_group_summary_zh=f"需求组{i}合并摘要内容",
            auto_action="auto_confirm", judge_mode="llm",
        ) if i < 6 else
        SemanticMergeJudgment(
            judgment_id=f"llm_j{i:03d}", merge_candidate_id=f"mc{i:03d}",
            cluster_id_a=f"ca{i:03d}", cluster_id_b=f"cb{i:03d}",
            decision="reject_merge", confidence=0.88,
            reason_zh=f"需求主题{i}工作流不同，不应合并。",
            auto_action="auto_reject", judge_mode="llm",
        )
        for i in range(8)
    ]
    paths = {
        "rule_j": tmp_path / "rule_judgments.jsonl",
        "llm_j": tmp_path / "llm_judgments.jsonl",
        "rule_groups": tmp_path / "rule_groups.jsonl",
        "llm_groups": tmp_path / "llm_groups.jsonl",
        "rule_exc": tmp_path / "rule_exceptions.jsonl",
        "llm_exc": tmp_path / "llm_exceptions.jsonl",
        "report": tmp_path / "comparison_report.md",
        "summary": tmp_path / "run_summary.json",
    }
    write_semantic_merge_judgments(rule_judgments, paths["rule_j"])
    write_semantic_merge_judgments(llm_judgments, paths["llm_j"])
    for p in (paths["rule_groups"], paths["llm_groups"], paths["rule_exc"], paths["llm_exc"]):
        p.write_text("", encoding="utf-8")
    return paths


def test_comparison_summary_correct_counts(tmp_path: Path):
    paths = _write_fixtures(tmp_path)
    summary = build_semantic_merge_comparison_report(
        rule_judgments_path=paths["rule_j"],
        llm_judgments_path=paths["llm_j"],
        rule_groups_path=paths["rule_groups"],
        llm_groups_path=paths["llm_groups"],
        rule_exceptions_path=paths["rule_exc"],
        llm_exceptions_path=paths["llm_exc"],
        report_path=paths["report"],
        run_summary_path=paths["summary"],
    )
    assert summary.rule_based_judgments == 8
    assert summary.llm_judgments == 8
    assert summary.llm_auto_confirmed == 6
    assert summary.llm_auto_rejected == 2
    assert summary.llm_human_exceptions == 0
    # rule_based_human_exceptions is read from the exception file (empty in this fixture)
    # The comparison report reads from exception jsonl, not re-computes from judgments
    assert summary.rule_based_judgments == 8
    assert summary.rule_based_auto_confirmed == 0  # 5 reject + 3 maybe, none confirmed


def test_decision_shift_matrix_counts(tmp_path: Path):
    paths = _write_fixtures(tmp_path)
    summary = build_semantic_merge_comparison_report(
        rule_judgments_path=paths["rule_j"],
        llm_judgments_path=paths["llm_j"],
        rule_groups_path=paths["rule_groups"],
        llm_groups_path=paths["llm_groups"],
        rule_exceptions_path=paths["rule_exc"],
        llm_exceptions_path=paths["llm_exc"],
        report_path=paths["report"],
        run_summary_path=paths["summary"],
    )
    # 5 rule_based reject (mc0-mc4), 3 maybe (mc5-mc7) -> LLM 6 confirm (mc0-mc5), 2 reject (mc6-mc7)
    # mc5: rb=maybe, llm=confirm => maybe_to_confirm = 1
    # mc6,mc7: rb=maybe, llm=reject => maybe_to_reject = 2
    # mc0-mc4: rb=reject, llm=confirm => reject_to_confirm = 5
    assert summary.maybe_to_confirm >= 1
    assert summary.maybe_to_reject >= 1
    assert summary.reject_to_confirm >= 3


def test_report_file_generated(tmp_path: Path):
    paths = _write_fixtures(tmp_path)
    build_semantic_merge_comparison_report(
        rule_judgments_path=paths["rule_j"],
        llm_judgments_path=paths["llm_j"],
        rule_groups_path=paths["rule_groups"],
        llm_groups_path=paths["llm_groups"],
        rule_exceptions_path=paths["rule_exc"],
        llm_exceptions_path=paths["llm_exc"],
        report_path=paths["report"],
        run_summary_path=paths["summary"],
    )
    assert paths["report"].exists()
    content = paths["report"].read_text(encoding="utf-8")
    assert "# LLM Semantic Merge Comparison Report" in content
    assert "Decision Shift Matrix" in content
    assert "Improvements" in content
    assert "Potential Risks" in content


def test_exception_rate_reduction_computed(tmp_path: Path):
    paths = _write_fixtures(tmp_path)
    summary = build_semantic_merge_comparison_report(
        rule_judgments_path=paths["rule_j"],
        llm_judgments_path=paths["llm_j"],
        rule_groups_path=paths["rule_groups"],
        llm_groups_path=paths["llm_groups"],
        rule_exceptions_path=paths["rule_exc"],
        llm_exceptions_path=paths["llm_exc"],
        report_path=paths["report"],
        run_summary_path=paths["summary"],
    )
    # rule exception rate = 0, llm exception rate = 0 in this test
    assert summary.exception_rate_reduction is not None


def test_readiness_source_is_llm_when_llm_exists(tmp_path: Path):
    paths = _write_fixtures(tmp_path)
    summary = build_semantic_merge_comparison_report(
        rule_judgments_path=paths["rule_j"],
        llm_judgments_path=paths["llm_j"],
        rule_groups_path=paths["rule_groups"],
        llm_groups_path=paths["llm_groups"],
        rule_exceptions_path=paths["rule_exc"],
        llm_exceptions_path=paths["llm_exc"],
        report_path=paths["report"],
        run_summary_path=paths["summary"],
    )
    assert summary.readiness_source == "llm"


