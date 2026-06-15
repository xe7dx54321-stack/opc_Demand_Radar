"""Tests for real_evidence_service (UI layer)."""
from __future__ import annotations
import json
from pathlib import Path
import demand_radar.ui.real_evidence_service as svc_mod


def _patch(monkeypatch, tmp_path, items=None, validations=None, reviews=None):
    items_p = tmp_path / "items.jsonl"
    val_p = tmp_path / "val.jsonl"
    rev_p = tmp_path / "reviews.jsonl"

    def write_jsonl(path, data):
        path.write_text(
            "\n".join(json.dumps(d, ensure_ascii=False) for d in data) + "\n",
            encoding="utf-8",
        )

    if items:
        write_jsonl(items_p, items)
    if validations:
        write_jsonl(val_p, validations)
    if reviews:
        write_jsonl(rev_p, reviews)

    monkeypatch.setattr(svc_mod, "_ITEMS_PATH", items_p)
    monkeypatch.setattr(svc_mod, "_VALIDATION_PATH", val_p)
    monkeypatch.setattr(svc_mod, "_REVIEWS_PATH", rev_p)


def test_summary_empty(tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    summary = svc_mod.get_real_evidence_summary()
    assert summary["evidence_items"] == 0
    assert summary["valid"] == 0


def test_summary_with_items(tmp_path, monkeypatch):
    items = [
        {
            "evidence_id": "re_001",
            "source_type": "product_review",
            "source_url": "https://example.com",
            "paid_alternative": "PitchBook",
            "current_solution": "spreadsheet",
        }
    ]
    validations = [{"evidence_id": "re_001", "status": "valid"}]
    _patch(monkeypatch, tmp_path, items=items, validations=validations)
    summary = svc_mod.get_real_evidence_summary()
    assert summary["evidence_items"] == 1
    assert summary["valid"] == 1
    assert summary["source_url_ratio"] == 1.0
    assert summary["user_voice_signals"] == 1


def test_get_items_returns_list(tmp_path, monkeypatch):
    items = [{"evidence_id": "re_001", "source_type": "blog_post"}]
    _patch(monkeypatch, tmp_path, items=items)
    result = svc_mod.get_real_evidence_items()
    assert len(result) == 1


def test_get_calibration_reviews(tmp_path, monkeypatch):
    reviews = [{"review_id": "cr_001", "evidence_id": "re_001", "human_labels": ["true_pain"]}]
    _patch(monkeypatch, tmp_path, reviews=reviews)
    result = svc_mod.get_calibration_reviews()
    assert len(result) == 1
    assert "true_pain" in result[0]["human_labels"]