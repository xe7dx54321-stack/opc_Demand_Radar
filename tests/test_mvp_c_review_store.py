"""Tests for PainSignalReviewStore."""
import pytest
from pathlib import Path
from demand_radar.mvp_c.review_store import PainSignalReviewStore
from demand_radar.mvp_c.review_schema import PainSignalReview
from demand_radar.mvp_b.pain_extraction_schema import ExtractedPainItem


def _make_review(pid="pain__000022", action="pursue", **kw):
    defaults = dict(true_pain=True, commercial_potential="high")
    defaults.update(kw)
    return PainSignalReview(
        review_id=f"rev_{pid}",
        pain_item_id=pid,
        candidate_id="cand_abc",
        action_decision=action,
        created_at="2026-01-01T00:00:00Z",
        **defaults,
    )


def _make_pain_item(pid, should_extract=True):
    kwargs = dict(
        pain_item_id=pid, candidate_id="c001",
        should_extract=should_extract,
        evidence_strength="medium" if should_extract else "reject",
        confidence=0.7,
        created_at="2026-01-01T00:00:00Z",
    )
    if should_extract:
        kwargs["evidence_quote"] = "We spend hours on research."
    else:
        kwargs["reject_reason"] = "Not relevant"
    return ExtractedPainItem(**kwargs)


def test_save_and_load(tmp_path):
    store = PainSignalReviewStore(path=tmp_path / "reviews.jsonl")
    rev = _make_review()
    store.save_review(rev)
    loaded = store.load_reviews()
    assert len(loaded) == 1
    assert loaded[0].pain_item_id == "pain__000022"


def test_upsert_overwrites(tmp_path):
    store = PainSignalReviewStore(path=tmp_path / "reviews.jsonl")
    rev1 = _make_review("pain__000022", action="watch")
    store.upsert_review(rev1)
    rev2 = _make_review("pain__000022", action="pursue")
    store.upsert_review(rev2)
    loaded = store.load_reviews()
    assert len(loaded) == 1
    assert loaded[0].action_decision == "pursue"


def test_upsert_different_ids(tmp_path):
    store = PainSignalReviewStore(path=tmp_path / "reviews.jsonl")
    store.upsert_review(_make_review("pain__000022"))
    store.upsert_review(_make_review("pain__000023"))
    loaded = store.load_reviews()
    assert len(loaded) == 2


def test_get_by_pain_item_id(tmp_path):
    store = PainSignalReviewStore(path=tmp_path / "reviews.jsonl")
    store.upsert_review(_make_review("pain__000022"))
    r = store.get_review_by_pain_item_id("pain__000022")
    assert r is not None
    assert r.pain_item_id == "pain__000022"


def test_get_missing_returns_none(tmp_path):
    store = PainSignalReviewStore(path=tmp_path / "reviews.jsonl")
    assert store.get_review_by_pain_item_id("nonexistent") is None


def test_does_not_create_file_on_load(tmp_path):
    path = tmp_path / "reviews.jsonl"
    store = PainSignalReviewStore(path=path)
    reviews = store.load_reviews()
    assert reviews == []
    assert not path.exists()


def test_does_not_modify_pain_items(tmp_path):
    """Store operations should not touch extracted_pain_items.jsonl."""
    pain_path = tmp_path / "extracted_pain_items.jsonl"
    pain_path.write_text('{"test": "original"}\n', encoding="utf-8")
    store = PainSignalReviewStore(path=tmp_path / "reviews.jsonl")
    store.upsert_review(_make_review())
    assert pain_path.read_text(encoding="utf-8") == '{"test": "original"}\n'


def test_build_summary(tmp_path):
    store = PainSignalReviewStore(path=tmp_path / "reviews.jsonl")
    store.upsert_review(_make_review("pain__000022", action="pursue"))
    store.upsert_review(_make_review("pain__000023", action="watch", commercial_potential="medium", true_pain=False))
    pain_items = [_make_pain_item("pain__000022"), _make_pain_item("pain__000023"), _make_pain_item("pain__000024")]
    summary = store.build_summary(pain_items)
    assert summary.total_pain_items == 3
    assert summary.reviewed_count == 2
    assert summary.unreviewed_count == 1
    assert summary.true_pain_count == 1
    assert summary.false_pain_count == 1
    assert summary.pursue_count == 1
    assert summary.watch_count == 1
