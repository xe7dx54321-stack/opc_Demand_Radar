"""Tests for ReviewService."""
import csv, json, pytest
from pathlib import Path
from demand_radar.mvp_c.review_service import ReviewService, PainSignalCard
from demand_radar.mvp_c.review_store import PainSignalReviewStore
from demand_radar.mvp_c.review_schema import PainSignalReview
from demand_radar.real_evidence.real_evidence_validator import TEMPLATE_COLUMNS


def _make_pain_jsonl(tmp_path, items):
    p = tmp_path / "extracted_pain_items.jsonl"
    lines = []
    for item in items:
        lines.append(json.dumps(item, ensure_ascii=False))
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def _pain_dict(pid, should_extract=True, strength="medium"):
    d = {
        "pain_item_id": pid,
        "candidate_id": f"cand_{pid}",
        "should_extract": should_extract,
        "evidence_strength": strength if should_extract else "reject",
        "confidence": 0.75,
        "created_at": "2026-01-01T00:00:00Z",
        "title": f"Test Signal {pid}",
        "source_url": f"https://example.com/{pid}",
        "source_type": "community_discussion",
        "persona": "VC analyst",
        "workflow_stage": "deal_sourcing",
        "pain_type": "manual_workflow",
        "pain_description_zh": "Test pain description",
        "evidence_quote": "We spend hours on this." if should_extract else None,
        "prompt_version": "test",
        "model": None,
    }
    if not should_extract:
        d["reject_reason"] = "Not relevant"
    return d


def _make_store(tmp_path, reviews=None):
    store = PainSignalReviewStore(path=tmp_path / "reviews.jsonl")
    if reviews:
        for r in reviews:
            store.upsert_review(r)
    return store


def test_loads_extracted_pain_items(tmp_path):
    p = _make_pain_jsonl(tmp_path, [_pain_dict("p001"), _pain_dict("p002")])
    svc = ReviewService(pain_items_path=p, store=_make_store(tmp_path))
    cards = svc.load_pain_signal_cards()
    assert len(cards) == 2


def test_filters_out_non_extracted(tmp_path):
    p = _make_pain_jsonl(tmp_path, [
        _pain_dict("p001", should_extract=True),
        _pain_dict("p002", should_extract=False),
    ])
    svc = ReviewService(pain_items_path=p, store=_make_store(tmp_path))
    cards = svc.load_pain_signal_cards(only_extracted=True)
    assert len(cards) == 1
    assert cards[0].pain_item_id == "p001"


def test_merges_existing_review(tmp_path):
    p = _make_pain_jsonl(tmp_path, [_pain_dict("p001")])
    rev = PainSignalReview(
        review_id="rev_p001", pain_item_id="p001",
        candidate_id="cand_p001", action_decision="pursue",
        created_at="2026-01-01T00:00:00Z",
    )
    store = _make_store(tmp_path, [rev])
    svc = ReviewService(pain_items_path=p, store=store)
    cards = svc.load_pain_signal_cards()
    assert cards[0].existing_review is not None
    assert cards[0].existing_review.action_decision == "pursue"


def test_filter_by_strength(tmp_path):
    p = _make_pain_jsonl(tmp_path, [
        _pain_dict("p001", strength="strong"),
        _pain_dict("p002", strength="medium"),
    ])
    svc = ReviewService(pain_items_path=p, store=_make_store(tmp_path))
    cards = svc.load_pain_signal_cards(filter_strength="strong")
    assert len(cards) == 1
    assert cards[0].evidence_strength == "strong"


def test_filter_reviewed_only(tmp_path):
    p = _make_pain_jsonl(tmp_path, [_pain_dict("p001"), _pain_dict("p002")])
    rev = PainSignalReview(
        review_id="rev_p001", pain_item_id="p001",
        candidate_id="cand_p001", action_decision="watch",
        created_at="2026-01-01T00:00:00Z",
    )
    store = _make_store(tmp_path, [rev])
    svc = ReviewService(pain_items_path=p, store=store)
    reviewed = svc.load_pain_signal_cards(reviewed_only=True)
    unreviewed = svc.load_pain_signal_cards(reviewed_only=False)
    assert len(reviewed) == 1
    assert len(unreviewed) == 1


def test_graceful_missing_pain_items(tmp_path):
    svc = ReviewService(pain_items_path=tmp_path / "nonexistent.jsonl", store=_make_store(tmp_path))
    cards = svc.load_pain_signal_cards()
    assert cards == []


def test_graceful_no_reviews(tmp_path):
    p = _make_pain_jsonl(tmp_path, [_pain_dict("p001")])
    svc = ReviewService(pain_items_path=p, store=_make_store(tmp_path))
    cards = svc.load_pain_signal_cards()
    assert cards[0].existing_review is None


def test_summary_counts(tmp_path):
    p = _make_pain_jsonl(tmp_path, [_pain_dict("p001"), _pain_dict("p002")])
    rev = PainSignalReview(
        review_id="rev_p001", pain_item_id="p001",
        candidate_id="cand_p001", action_decision="pursue",
        true_pain=True, commercial_potential="high",
        extraction_quality="good",
        created_at="2026-01-01T00:00:00Z",
    )
    store = _make_store(tmp_path, [rev])
    svc = ReviewService(pain_items_path=p, store=store)
    summary = svc.get_summary()
    assert summary.total_pain_items == 2
    assert summary.reviewed_count == 1
    assert summary.pursue_count == 1
    assert summary.commercial_high_count == 1
    assert summary.extraction_good_count == 1
