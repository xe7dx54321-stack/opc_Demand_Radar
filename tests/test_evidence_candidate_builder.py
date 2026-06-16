"""Tests for evidence_candidate_builder."""
from __future__ import annotations
import pytest
from opc_foundation.signals.raw_signal_schema import RawSignal
from opc_foundation.run.time_utils import utcnow_iso
from opc_foundation.signals.dedupe import hash_url, hash_text
from demand_radar.acquisition.evidence_candidate_builder import (
    build_evidence_candidate,
    build_evidence_candidates,
)


def _sig(**kw):
    defaults = dict(
        signal_id="sig_001",
        source_id="hacker_news_ai_investment",
        source_type="community_discussion",
        source_name="Hacker News",
        source_url="https://news.ycombinator.com/item?id=12345",
        raw_text="We spend 4 hours every week manually tracking AI startups across blogs, GitHub, and newsletters. Very tedious.",
        fetched_at=utcnow_iso(),
        url_hash=hash_url("https://news.ycombinator.com/item?id=12345"),
        content_hash=hash_text("We spend 4 hours every week manually tracking AI startups across blogs, GitHub, and newsletters. Very tedious."),
    )
    defaults.update(kw)
    return RawSignal(**defaults)


def test_valid_candidate_from_signal():
    sig = _sig()
    seen_url: set = set()
    seen_content: set = set()
    c = build_evidence_candidate(sig, "ai_investment_tracking", "AI 产业跟踪", seen_url, seen_content)
    assert c.validation_status == "valid"
    assert c.include_in_evidence_pack is True
    assert c.source_weight == 0.90


def test_short_text_invalid():
    sig = _sig(raw_text="Too short.", source_url="https://x.com/a", url_hash=None, content_hash=None)
    seen_url: set = set()
    seen_content: set = set()
    c = build_evidence_candidate(sig, "ai_investment_tracking", "AI 产业跟踪", seen_url, seen_content)
    assert c.validation_status == "invalid"
    assert c.include_in_evidence_pack is False
    assert any("too short" in r.lower() for r in c.validation_reasons)


def test_duplicate_by_url_hash():
    sig = _sig()
    seen_url = {sig.url_hash}
    seen_content: set = set()
    c = build_evidence_candidate(sig, "ai_investment_tracking", "AI", seen_url, seen_content)
    assert c.validation_status == "duplicate"


def test_source_weight_community_discussion():
    sig = _sig(source_type="community_discussion")
    seen_url: set = set()
    seen_content: set = set()
    c = build_evidence_candidate(sig, "ai_investment_tracking", "AI", seen_url, seen_content)
    assert c.source_weight >= 0.85


def test_source_weight_rss():
    sig = _sig(source_type="rss", url_hash=None, content_hash=None)
    seen_url: set = set()
    seen_content: set = set()
    c = build_evidence_candidate(sig, "ai_investment_tracking", "AI", seen_url, seen_content)
    assert c.source_weight <= 0.65


def test_paid_signal_detected():
    sig = _sig(raw_text="We pay $200/month for a market intelligence subscription but still do manual tracking for most companies.", url_hash=None)
    seen_url: set = set()
    seen_content: set = set()
    c = build_evidence_candidate(sig, "ai_investment_tracking", "AI", seen_url, seen_content)
    assert "paid_signal" in c.detected_signal_types


def test_workaround_signal_detected():
    sig = _sig(raw_text="Our team uses an Excel spreadsheet and Notion to manually track AI company news and funding rounds each week.", url_hash=None)
    seen_url: set = set()
    seen_content: set = set()
    c = build_evidence_candidate(sig, "ai_investment_tracking", "AI", seen_url, seen_content)
    assert "workaround_signal" in c.detected_signal_types


def test_build_evidence_candidates_batch():
    sigs = [_sig(signal_id=f"sig_{i}", source_url=f"https://example.com/{i}", url_hash=hash_url(f"https://example.com/{i}"), content_hash=hash_text(f"Content {i} AI tracking manually hours every week")) for i in range(3)]
    candidates = build_evidence_candidates(sigs, "ai_investment_tracking", "AI 产业跟踪")
    assert len(candidates) == 3
