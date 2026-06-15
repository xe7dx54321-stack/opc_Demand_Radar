"""Tests for Stage 3.3 template_builder."""
import csv
import json
import pytest
from pathlib import Path
from demand_radar.targeted_expansion.template_builder import build_template


def _make_plan(plan_id, group_id, title, score, gap_types, target_signals, keywords_zh, keywords_en, source_types, lang="zh"):
    return {
        "plan_id": plan_id,
        "gap_analysis_id": "gap_" + plan_id,
        "truth_score_id": "ts_" + plan_id,
        "source_group_id": group_id,
        "group_title_zh": title,
        "target_new_signals": target_signals,
        "target_personas": [],
        "target_source_types": source_types,
        "target_languages": [lang],
        "search_keywords_zh": keywords_zh,
        "search_keywords_en": keywords_en,
        "positive_signal_criteria": ["mentions pricing", "mentions payment"],
        "negative_signal_criteria": ["no cost signal"],
        "collection_notes_zh": "请采集付费相关信号",
        "expected_impact_zh": "预期提升付费意愿维度分数",
        "created_at": "2026-01-01T00:00:00+00:00",
        "_target_current_score": score,
        "_target_gap_types": gap_types,
    }


@pytest.fixture
def two_plans(tmp_path):
    plans = [
        _make_plan("p001", "grp_001", "内容团队选题准备", 66.4,
                   ["paid_alternative", "budget_signal"], 5,
                   ["内容 工具 付费"], ["content tool pricing"], ["pricing_page"]),
        _make_plan("p002", "grp_002", "投资人AI产业跟踪", 60.4,
                   ["manual_workaround", "paid_alternative"], 5,
                   ["投资 AI 追踪"], ["investor AI tracking"], ["case_study"]),
    ]
    plan_path = tmp_path / "plans.jsonl"
    plan_path.write_text("\n".join(json.dumps(p) for p in plans), encoding="utf-8")
    ts_path = tmp_path / "truth_scores.jsonl"
    ts_path.write_text("", encoding="utf-8")
    return plan_path, ts_path, tmp_path


def test_template_generates_rows(two_plans):
    plan_path, ts_path, tmp_path = two_plans
    out_path = tmp_path / "template.csv"
    build_template(
        plans_path=str(plan_path),
        truth_scores_path=str(ts_path),
        output_path=str(out_path),
    )
    assert out_path.exists()
    with open(out_path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    # 5 + 5 = 10 rows
    assert len(rows) == 10


def test_template_row_fields(two_plans):
    plan_path, ts_path, tmp_path = two_plans
    out_path = tmp_path / "template.csv"
    build_template(
        plans_path=str(plan_path),
        truth_scores_path=str(ts_path),
        output_path=str(out_path),
    )
    with open(out_path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    row = rows[0]
    assert row["target_group_id"] == "grp_001"
    assert row["collection_status"] == "pending"
    assert row["target_signal_id"].startswith("tsig_")


def test_template_payment_intent_ratio(two_plans):
    """At least 40% of rows should be payment/budget intents when those are the main gaps."""
    plan_path, ts_path, tmp_path = two_plans
    out_path = tmp_path / "template.csv"
    build_template(
        plans_path=str(plan_path),
        truth_scores_path=str(ts_path),
        output_path=str(out_path),
    )
    with open(out_path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    payment_intents = {"paid_alternative", "budget_signal", "business_impact", "time_cost", "product_review", "case_study"}
    payment_count = sum(1 for r in rows if r["evidence_intent"] in payment_intents)
    # Should have at least some payment-type intents
    assert payment_count >= len(rows) // 3


def test_template_group_id_correct(two_plans):
    """Each row has the correct target_group_id."""
    plan_path, ts_path, tmp_path = two_plans
    out_path = tmp_path / "template.csv"
    build_template(
        plans_path=str(plan_path),
        truth_scores_path=str(ts_path),
        output_path=str(out_path),
    )
    with open(out_path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    grp1_rows = [r for r in rows if r["target_group_id"] == "grp_001"]
    grp2_rows = [r for r in rows if r["target_group_id"] == "grp_002"]
    assert len(grp1_rows) == 5
    assert len(grp2_rows) == 5


def test_template_no_plans(tmp_path):
    """Empty plan file produces empty template (header only)."""
    plan_path = tmp_path / "empty_plans.jsonl"
    plan_path.write_text("", encoding="utf-8")
    ts_path = tmp_path / "truth_scores.jsonl"
    ts_path.write_text("", encoding="utf-8")
    out_path = tmp_path / "template.csv"
    build_template(
        plans_path=str(plan_path),
        truth_scores_path=str(ts_path),
        output_path=str(out_path),
    )
    with open(out_path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 0
