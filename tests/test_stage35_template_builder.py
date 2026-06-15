"""Tests for Stage 3.5 template builder."""
import csv
import json
import pytest
from pathlib import Path
from demand_radar.stage35.stage35_template_builder import build_stage35_template, _allocate_intents

NOW = "2026-01-01T00:00:00+00:00"

_PAYMENT_OR_COST = {"paid_alternative", "budget_signal", "business_impact", "time_cost"}
_WORKAROUND = {"current_solution", "manual_workaround"}


def _make_candidate_file(tmp_path, candidates):
    p = tmp_path / "selected.jsonl"
    p.write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in candidates) + "\n", encoding="utf-8")
    return p


def _cand(gid, title, rank=1):
    return {
        "selected_candidate_id": f"s35cand_{gid}",
        "truth_score_id": f"ts_{gid}",
        "source_group_id": gid,
        "group_title_zh": title,
        "current_truth_score": 62.0,
        "current_truth_level": "medium",
        "current_next_action": "needs_more_evidence",
        "selected_reason_zh": "匹配",
        "priority_rank": rank,
        "target_new_signals": 12,
        "target_evidence_intents": ["paid_alternative", "budget_signal"],
        "created_at": NOW,
    }


def test_template_exactly_24_rows(tmp_path):
    sel_path = _make_candidate_file(tmp_path, [_cand("g1", "企业知识工作流")])
    out = tmp_path / "template.csv"
    rows = build_stage35_template(selected_candidates_path=sel_path, output_path=out, total_rows=24)
    assert len(rows) == 24


def test_payment_or_cost_ratio_at_least_60pct(tmp_path):
    """paid_alternative / budget_signal / business_impact / time_cost >= 60%."""
    sel_path = _make_candidate_file(tmp_path, [_cand("g1", "企业知识工作流")])
    out = tmp_path / "template.csv"
    rows = build_stage35_template(selected_candidates_path=sel_path, output_path=out, total_rows=24)
    pay_n = sum(1 for r in rows if r.get("evidence_intent") in _PAYMENT_OR_COST)
    ratio = pay_n / len(rows)
    assert ratio >= 0.60, f"payment_or_cost ratio {ratio:.2%} < 60% (pay_n={pay_n}, total={len(rows)})"


def test_workaround_ratio_at_least_25pct(tmp_path):
    """current_solution / manual_workaround >= 25%."""
    sel_path = _make_candidate_file(tmp_path, [_cand("g1", "企业知识工作流")])
    out = tmp_path / "template.csv"
    rows = build_stage35_template(selected_candidates_path=sel_path, output_path=out, total_rows=24)
    wa_n = sum(1 for r in rows if r.get("evidence_intent") in _WORKAROUND)
    ratio = wa_n / len(rows)
    assert ratio >= 0.25, f"workaround ratio {ratio:.2%} < 25% (wa_n={wa_n}, total={len(rows)})"


def test_payment_or_cost_absolute_count(tmp_path):
    """For 24 rows, payment/cost count >= 14 (floor of 60%)."""
    sel_path = _make_candidate_file(tmp_path, [_cand("g1", "企业知识工作流")])
    out = tmp_path / "template.csv"
    rows = build_stage35_template(selected_candidates_path=sel_path, output_path=out, total_rows=24)
    pay_n = sum(1 for r in rows if r.get("evidence_intent") in _PAYMENT_OR_COST)
    assert pay_n >= 14


def test_template_has_required_columns(tmp_path):
    sel_path = _make_candidate_file(tmp_path, [_cand("g1", "企业知识工作流")])
    out = tmp_path / "template.csv"
    build_stage35_template(selected_candidates_path=sel_path, output_path=out, total_rows=12)
    with open(out, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames or []
    assert "target_signal_id" in cols
    assert "evidence_intent" in cols
    assert "stage35_collection_hint_zh" in cols


def test_empty_candidates_returns_empty(tmp_path):
    sel_path = tmp_path / "empty.jsonl"
    sel_path.write_text("\n", encoding="utf-8")
    out = tmp_path / "template.csv"
    rows = build_stage35_template(selected_candidates_path=sel_path, output_path=out)
    assert rows == []


def test_allocate_intents_payment_or_cost_gte_60pct():
    """_allocate_intents must produce >= 60% payment/cost for any n."""
    for n in [12, 24, 10, 14]:
        intents = _allocate_intents(n)
        pay_n = sum(1 for i in intents if i in _PAYMENT_OR_COST)
        assert pay_n / n >= 0.60, f"n={n}: pay_n={pay_n}, ratio={pay_n/n:.2%}"


def test_allocate_intents_workaround_gte_25pct():
    """_allocate_intents must produce >= 25% workaround for any n."""
    for n in [12, 24, 10, 14]:
        intents = _allocate_intents(n)
        wa_n = sum(1 for i in intents if i in _WORKAROUND)
        assert wa_n / n >= 0.25, f"n={n}: wa_n={wa_n}, ratio={wa_n/n:.2%}"


def test_two_candidates_produce_24_rows(tmp_path):
    """Two candidates should still yield exactly total_rows=24."""
    sel_path = _make_candidate_file(tmp_path, [
        _cand("g1", "企业知识工作流", rank=1),
        _cand("g2", "投资人AI产业跟踪", rank=2),
    ])
    out = tmp_path / "template.csv"
    rows = build_stage35_template(selected_candidates_path=sel_path, output_path=out, total_rows=24)
    assert len(rows) == 24
    pay_n = sum(1 for r in rows if r.get("evidence_intent") in _PAYMENT_OR_COST)
    assert pay_n / 24 >= 0.60
