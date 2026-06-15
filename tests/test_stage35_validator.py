"""Tests for Stage 3.5 validator."""
import csv
import pytest
from pathlib import Path
from demand_radar.stage35.stage35_validator import validate_stage35_signals


def _write_csv(path, rows):
    cols = [
        "target_signal_id", "target_group_id", "target_truth_score_id",
        "evidence_intent", "raw_text", "url", "source_note",
        "is_synthetic", "exclude_from_truth_scoring", "collection_status",
    ]
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def _row(sig_id="s35_001", group="grp_001", score_id="ts_001",
         intent="paid_alternative",
         raw_text="This team pays for Notion AI and other tools at $50/user/month, totaling $2000/month.",
         url="https://example.com",
         synthetic="false", exclude="false", status="collected"):
    return {
        "target_signal_id": sig_id, "target_group_id": group,
        "target_truth_score_id": score_id, "evidence_intent": intent,
        "raw_text": raw_text, "url": url, "source_note": "",
        "is_synthetic": synthetic, "exclude_from_truth_scoring": exclude,
        "collection_status": status,
    }


def test_valid_paid_alternative_passes(tmp_path):
    p = tmp_path / "signals.csv"
    _write_csv(p, [_row()])
    out = tmp_path / "val.jsonl"
    results = validate_stage35_signals(p, output_path=out)
    assert len(results) == 1
    assert results[0]["status"] in ("valid", "warning")
    assert results[0]["include_in_combined_input"] is True


def test_synthetic_rejected(tmp_path):
    p = tmp_path / "signals.csv"
    _write_csv(p, [_row(synthetic="true")])
    out = tmp_path / "val.jsonl"
    results = validate_stage35_signals(p, output_path=out)
    assert results[0]["status"] == "invalid"
    assert results[0]["include_in_combined_input"] is False


def test_raw_text_too_short_rejected(tmp_path):
    p = tmp_path / "signals.csv"
    _write_csv(p, [_row(raw_text="short")])
    out = tmp_path / "val.jsonl"
    results = validate_stage35_signals(p, output_path=out, min_raw_text_chars=80)
    assert results[0]["status"] == "invalid"


def test_missing_source_rejected(tmp_path):
    p = tmp_path / "signals.csv"
    _write_csv(p, [_row(url="")])
    out = tmp_path / "val.jsonl"
    results = validate_stage35_signals(p, output_path=out)
    assert results[0]["status"] == "invalid"


def test_paid_intent_no_payment_keywords_is_warning(tmp_path):
    p = tmp_path / "signals.csv"
    long_text = "The team uses various tools to aggregate information across different platforms every week." * 2
    _write_csv(p, [_row(raw_text=long_text)])
    out = tmp_path / "val.jsonl"
    results = validate_stage35_signals(p, output_path=out)
    # No payment keywords: should be warning but still included
    assert results[0]["status"] == "warning"
    assert results[0]["include_in_combined_input"] is True


def test_pending_not_validated(tmp_path):
    p = tmp_path / "signals.csv"
    _write_csv(p, [_row(status="pending")])
    out = tmp_path / "val.jsonl"
    results = validate_stage35_signals(p, output_path=out)
    assert len(results) == 0  # pending rows are skipped


def test_missing_group_id_rejected(tmp_path):
    p = tmp_path / "signals.csv"
    _write_csv(p, [_row(group="")])
    out = tmp_path / "val.jsonl"
    results = validate_stage35_signals(p, output_path=out)
    assert results[0]["status"] == "invalid"


def test_workaround_intent_keyword_check(tmp_path):
    p = tmp_path / "signals.csv"
    good_text = "We currently use Excel spreadsheets to manually track and update information across departments." * 2
    _write_csv(p, [_row(intent="manual_workaround", raw_text=good_text, url="https://x.com")])
    out = tmp_path / "val.jsonl"
    results = validate_stage35_signals(p, output_path=out)
    assert results[0]["status"] in ("valid", "warning")
    assert "workaround_signal" in results[0]["detected_signal_types"]


def test_output_file_created(tmp_path):
    p = tmp_path / "signals.csv"
    _write_csv(p, [_row()])
    out = tmp_path / "val.jsonl"
    validate_stage35_signals(p, output_path=out)
    assert out.exists()
