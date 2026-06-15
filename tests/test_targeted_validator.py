"""Tests for Stage 3.3 targeted_validator."""
import csv
import json
import pytest
from pathlib import Path
from demand_radar.targeted_expansion.targeted_validator import validate_targeted_signals, load_validations


def _write_csv(tmp_path, rows):
    """Write a list of dicts to CSV and return path."""
    if not rows:
        return tmp_path / "empty.csv"
    p = tmp_path / "signals.csv"
    fieldnames = list(rows[0].keys())
    with open(p, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return p


def _base_row(**kwargs):
    defaults = {
        "target_signal_id": "tsig_000001",
        "target_group_id": "grp_001",
        "target_group_title_zh": "测试候选",
        "evidence_intent": "paid_alternative",
        "collection_status": "pending",
        "is_synthetic": "false",
        "exclude_from_truth_scoring": "false",
        "batch_id": "batch_stage33_targeted",
        "raw_text": "",
        "url": "",
        "source_note": "",
        "title": "",
        "target_gap_types": "",
        "suggested_keywords": "",
        "domain_tags": "",
    }
    defaults.update(kwargs)
    return defaults


def test_collected_empty_raw_text_is_invalid(tmp_path):
    rows = [_base_row(collection_status="collected", raw_text="", target_signal_id="tsig_000001")]
    p = _write_csv(tmp_path, rows)
    out = tmp_path / "validation.jsonl"
    result = validate_targeted_signals(str(p), str(out))
    assert len(result) == 1
    v = result[0]
    assert v.status == "invalid"
    assert any("raw_text" in e for e in v.validation_errors)


def test_no_url_no_source_note_is_invalid(tmp_path):
    rows = [_base_row(
        collection_status="collected",
        raw_text="Some important content about pricing.",
        url="",
        source_note="",
        target_signal_id="tsig_000002",
    )]
    p = _write_csv(tmp_path, rows)
    out = tmp_path / "validation.jsonl"
    result = validate_targeted_signals(str(p), str(out))
    assert len(result) == 1
    v = result[0]
    assert v.status == "invalid"
    assert any("source" in e for e in v.validation_errors)


def test_synthetic_must_exclude(tmp_path):
    rows = [_base_row(
        is_synthetic="true",
        exclude_from_truth_scoring="false",
        collection_status="collected",
        raw_text="synthetic content",
        url="https://example.com",
        target_signal_id="tsig_000003",
    )]
    p = _write_csv(tmp_path, rows)
    out = tmp_path / "validation.jsonl"
    result = validate_targeted_signals(str(p), str(out))
    assert len(result) == 1
    v = result[0]
    assert v.status == "invalid"
    assert any("synthetic" in e for e in v.validation_errors)


def test_synthetic_excluded_not_in_combined(tmp_path):
    rows = [_base_row(
        is_synthetic="true",
        exclude_from_truth_scoring="true",
        collection_status="collected",
        raw_text="synthetic content",
        url="https://example.com",
        target_signal_id="tsig_000004",
    )]
    p = _write_csv(tmp_path, rows)
    out = tmp_path / "validation.jsonl"
    result = validate_targeted_signals(str(p), str(out))
    assert len(result) == 1
    v = result[0]
    assert v.status == "excluded"
    assert v.include_in_combined_input is False


def test_paid_intent_with_payment_keywords_detected(tmp_path):
    rows = [_base_row(
        collection_status="collected",
        raw_text="We pay $500/month for this tool and the budget is high.",
        url="https://example.com",
        evidence_intent="paid_alternative",
        target_signal_id="tsig_000005",
    )]
    p = _write_csv(tmp_path, rows)
    out = tmp_path / "validation.jsonl"
    result = validate_targeted_signals(str(p), str(out))
    v = result[0]
    assert "payment_signal" in v.detected_signal_types
    assert v.status == "valid"


def test_paid_intent_without_payment_keywords_warning(tmp_path):
    rows = [_base_row(
        collection_status="collected",
        raw_text="We use this product but find it hard to search.",
        url="https://example.com",
        evidence_intent="paid_alternative",
        target_signal_id="tsig_000006",
    )]
    p = _write_csv(tmp_path, rows)
    out = tmp_path / "validation.jsonl"
    result = validate_targeted_signals(str(p), str(out))
    v = result[0]
    assert v.status == "warning"
    assert "payment_signal" not in v.detected_signal_types


def test_manual_workaround_detected(tmp_path):
    rows = [_base_row(
        collection_status="collected",
        raw_text="We manually copy data into a spreadsheet every day.",
        url="https://example.com",
        evidence_intent="manual_workaround",
        target_signal_id="tsig_000007",
    )]
    p = _write_csv(tmp_path, rows)
    out = tmp_path / "validation.jsonl"
    result = validate_targeted_signals(str(p), str(out))
    v = result[0]
    assert "workaround_signal" in v.detected_signal_types


def test_pending_status_not_in_combined(tmp_path):
    rows = [_base_row(collection_status="pending", target_signal_id="tsig_000008")]
    p = _write_csv(tmp_path, rows)
    out = tmp_path / "validation.jsonl"
    result = validate_targeted_signals(str(p), str(out))
    v = result[0]
    assert v.include_in_combined_input is False


def test_valid_collected_row(tmp_path):
    rows = [_base_row(
        collection_status="collected",
        raw_text="We pay for a SaaS tool and the subscription fee is $200/month.",
        url="https://example.com",
        evidence_intent="paid_alternative",
        target_signal_id="tsig_000009",
    )]
    p = _write_csv(tmp_path, rows)
    out = tmp_path / "validation.jsonl"
    result = validate_targeted_signals(str(p), str(out))
    v = result[0]
    assert v.status == "valid"
    assert v.include_in_combined_input is True


def test_load_validations(tmp_path):
    rows = [
        _base_row(collection_status="collected", raw_text="pay $300", url="https://a.com",
                  evidence_intent="budget_signal", target_signal_id="tsig_0001"),
        _base_row(collection_status="pending", target_signal_id="tsig_0002"),
    ]
    p = _write_csv(tmp_path, rows)
    out = tmp_path / "val.jsonl"
    validate_targeted_signals(str(p), str(out))
    loaded = load_validations(str(out))
    assert len(loaded) == 2


def test_load_validations_empty_file(tmp_path):
    out = tmp_path / "empty_val.jsonl"
    assert load_validations(str(out)) == []
