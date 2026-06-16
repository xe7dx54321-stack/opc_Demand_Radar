"""Tests for MVP-C real pain signal gate."""
import json
import pytest
from pathlib import Path
from demand_radar.mvp_c.real_pain_signal_gate import (
    is_real_reviewable_pain_signal,
    run_gate,
    build_gate_report,
    quarantine_stale_reviews,
    GateResult,
)
from demand_radar.mvp_c.review_service import ReviewService
from demand_radar.mvp_c.review_store import PainSignalReviewStore
from demand_radar.mvp_c.review_schema import PainSignalReview


def _item(pid="p001", url="https://thesisboard.com/", strength="strong",
          should_extract=True, stype="community_discussion", **kw):
    d = {
        "pain_item_id": pid,
        "candidate_id": f"cand_{pid}",
        "should_extract": should_extract,
        "evidence_strength": strength if should_extract else "reject",
        "source_url": url,
        "source_type": stype,
        "title": "ThesisBoard Investment Research",
        "pain_description_zh": "Analysts spend hours on manual tracking.",
        "evidence_quote": "We spend hours manually tracking startups.",
        "confidence": 0.85,
        "created_at": "2026-01-01T00:00:00Z",
        "metadata": {},
    }
    if not should_extract:
        d["reject_reason"] = "Not relevant"
        d.pop("evidence_quote", None)
    d.update(kw)
    return d


# ---- is_real_reviewable_pain_signal tests ----

def test_good_signal_allowed():
    r = is_real_reviewable_pain_signal(_item())
    assert r.allow is True
    assert r.block_reason is None


def test_example_com_blocked():
    r = is_real_reviewable_pain_signal(_item(url="https://example.com/test"))
    assert r.allow is False
    assert "example.com" in (r.block_reason or "").lower()


def test_example_org_blocked():
    r = is_real_reviewable_pain_signal(_item(url="https://example.org"))
    assert r.allow is False


def test_example_net_blocked():
    r = is_real_reviewable_pain_signal(_item(url="http://www.example.net/page"))
    assert r.allow is False


def test_should_extract_false_blocked():
    r = is_real_reviewable_pain_signal(_item(should_extract=False, url="https://thesisboard.com/"))
    assert r.allow is False
    assert "should_extract" in (r.block_reason or "").lower()


def test_weak_strength_blocked():
    r = is_real_reviewable_pain_signal(_item(strength="weak"))
    assert r.allow is False
    assert "evidence_strength" in (r.block_reason or "").lower()


def test_reject_strength_blocked():
    r = is_real_reviewable_pain_signal(_item(strength="reject"))
    assert r.allow is False


def test_missing_source_url_blocked():
    r = is_real_reviewable_pain_signal(_item(url=""))
    assert r.allow is False
    assert "source_url" in (r.block_reason or "").lower()


def test_none_source_url_blocked():
    item = _item()
    item["source_url"] = None
    r = is_real_reviewable_pain_signal(item)
    assert r.allow is False


def test_manual_seed_source_type_blocked():
    r = is_real_reviewable_pain_signal(_item(stype="manual_seed"))
    assert r.allow is False
    assert "source_type" in (r.block_reason or "").lower()


def test_placeholder_source_type_blocked():
    r = is_real_reviewable_pain_signal(_item(stype="placeholder"))
    assert r.allow is False


def test_inherited_sample_source_type_blocked():
    r = is_real_reviewable_pain_signal(_item(stype="inherited_sample"))
    assert r.allow is False


def test_synthetic_metadata_blocked():
    r = is_real_reviewable_pain_signal(_item(metadata={"synthetic": True}))
    assert r.allow is False


def test_exclude_from_scoring_metadata_blocked():
    r = is_real_reviewable_pain_signal(_item(metadata={"exclude_from_scoring": True}))
    assert r.allow is False


def test_missing_all_core_fields_blocked():
    item = _item()
    item["title"] = None
    item["pain_description_zh"] = None
    item["evidence_quote"] = None
    r = is_real_reviewable_pain_signal(item)
    assert r.allow is False


def test_domain_exclude_relevance_blocked():
    rel = {"relevance_decision": "exclude", "candidate_id": "cand_p001"}
    r = is_real_reviewable_pain_signal(_item(), relevance=rel)
    assert r.allow is False


def test_domain_include_relevance_allowed():
    rel = {"relevance_decision": "include", "candidate_id": "cand_p001"}
    r = is_real_reviewable_pain_signal(_item(), relevance=rel)
    assert r.allow is True


def test_medium_strength_allowed():
    r = is_real_reviewable_pain_signal(_item(strength="medium"))
    assert r.allow is True


# ---- run_gate tests ----

def test_run_gate_separates_allowed_blocked():
    items = [
        _item("p001", url="https://thesisboard.com/"),
        _item("p002", url="https://example.com/"),
        _item("p003", url="https://meticulate.ai/", strength="medium"),
    ]
    allowed, blocked = run_gate(items)
    allowed_ids = {r.pain_item_id for r in allowed}
    blocked_ids = {r.pain_item_id for r in blocked}
    assert "p001" in allowed_ids
    assert "p002" in blocked_ids
    assert "p003" in allowed_ids
    assert "p002" not in allowed_ids


def test_run_gate_all_real_signals_pass():
    items = [
        _item("p001", url="https://thesisboard.com/"),
        _item("p002", url="https://news.ycombinator.com/item?id=123"),
        _item("p003", url="https://agents.decodeinvesting.com", strength="medium"),
    ]
    allowed, blocked = run_gate(items)
    assert len(allowed) == 3
    assert len(blocked) == 0


# ---- Gate report test ----

def test_gate_report_created(tmp_path):
    items = [_item("p001"), _item("p002", url="https://example.com/")]
    allowed, blocked = run_gate(items)
    out = tmp_path / "gate_report.md"
    build_gate_report(items, allowed, blocked, output_path=out)
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "Gate Report" in content
    assert "reviewable_count: 1" in content
    assert "blocked_count: 1" in content
    assert "example.com items blocked: 1" in content
    assert "example.com items passed (SHOULD BE 0): 0" in content
    assert "PASS" in content


# ---- Quarantine tests ----

def test_quarantine_moves_blocked_reviews(tmp_path):
    rev_path = tmp_path / "reviews.jsonl"
    quar_path = tmp_path / "quarantined.jsonl"
    # Write reviews for p001 (allowed) and p002 (blocked)
    rev_path.write_text(
        json.dumps({"pain_item_id": "p001", "review_id": "r1", "action_decision": "pursue"}) + "\n" +
        json.dumps({"pain_item_id": "p002", "review_id": "r2", "action_decision": "watch"}) + "\n",
        encoding="utf-8",
    )
    kept, quarantined = quarantine_stale_reviews(rev_path, {"p001"}, quar_path)
    assert kept == 1
    assert quarantined == 1
    remaining = [json.loads(l) for l in rev_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(remaining) == 1
    assert remaining[0]["pain_item_id"] == "p001"
    q = [json.loads(l) for l in quar_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(q) == 1
    assert q[0]["pain_item_id"] == "p002"


def test_quarantine_no_reviews_file(tmp_path):
    kept, quarantined = quarantine_stale_reviews(tmp_path / "nonexistent.jsonl", {"p001"})
    assert kept == 0
    assert quarantined == 0


def test_quarantined_not_in_summary(tmp_path):
    """Reviews for blocked items do not count in the review summary."""
    pain_path = tmp_path / "extracted_pain_items.jsonl"
    pain_items = [
        _item("p001", url="https://thesisboard.com/"),   # will pass gate
        _item("p002", url="https://example.com/"),        # will be blocked
    ]
    pain_path.write_text(
        "\n".join(json.dumps(i) for i in pain_items) + "\n",
        encoding="utf-8",
    )
    rev_path = tmp_path / "reviews.jsonl"
    rev_path.write_text(
        json.dumps({"pain_item_id": "p001", "review_id": "r1", "action_decision": "pursue",
                    "candidate_id": "c1", "created_at": "2026-01-01T00:00:00Z"}) + "\n" +
        json.dumps({"pain_item_id": "p002", "review_id": "r2", "action_decision": "watch",
                    "candidate_id": "c2", "created_at": "2026-01-01T00:00:00Z"}) + "\n",
        encoding="utf-8",
    )
    # Quarantine p002 reviews
    quarantine_stale_reviews(rev_path, {"p001"})

    store = PainSignalReviewStore(path=rev_path)
    svc = ReviewService(pain_items_path=pain_path, store=store)
    summary = svc.get_summary()
    # Only p001 is reviewable, only p001's review counts
    assert summary.total_pain_items == 1  # only allowed items
    assert summary.reviewed_count == 1
    assert summary.pursue_count == 1


def test_ui_service_returns_only_allowed(tmp_path):
    """ReviewService.load_pain_signal_cards() returns only gate-allowed items."""
    pain_path = tmp_path / "extracted_pain_items.jsonl"
    pain_items = [
        _item("p001", url="https://thesisboard.com/"),
        _item("p002", url="https://example.com/"),
        _item("p003", url="", should_extract=True, strength="medium"),  # no URL - blocked
    ]
    # Fix p003 to have evidence_quote etc even without url
    pain_path.write_text(
        "\n".join(json.dumps(i) for i in pain_items) + "\n",
        encoding="utf-8",
    )
    store = PainSignalReviewStore(path=tmp_path / "reviews.jsonl")
    svc = ReviewService(pain_items_path=pain_path, store=store)
    cards = svc.load_pain_signal_cards()
    card_ids = [c.pain_item_id for c in cards]
    assert "p001" in card_ids
    assert "p002" not in card_ids
    assert "p003" not in card_ids
