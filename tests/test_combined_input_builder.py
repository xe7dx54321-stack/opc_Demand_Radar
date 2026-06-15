"""Tests for Stage 3.3 combined_input_builder."""
import csv
import json
import pytest
from pathlib import Path
from demand_radar.targeted_expansion.combined_input_builder import build_combined_input
from demand_radar.targeted_expansion.targeted_schema import TargetedSignalValidation
from datetime import datetime, timezone


def _write_csv(path, rows, fieldnames=None):
    if not rows:
        if fieldnames:
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
        return path
    if fieldnames is None:
        fieldnames = list(rows[0].keys())
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def _write_validations(path, validations):
    with open(path, "w", encoding="utf-8") as f:
        for v in validations:
            f.write(v.model_dump_json() + "\n")


def _make_validation(sig_id, include, status="valid"):
    return TargetedSignalValidation(
        validation_id=f"val_{sig_id}",
        target_signal_id=sig_id,
        status=status,
        include_in_combined_input=include,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def test_base_rows_only(tmp_path):
    """With no targeted file, combined = base only."""
    base_rows = [
        {"url": "https://a.com", "raw_text": "Signal A", "batch_id": "batch_1"},
        {"url": "https://b.com", "raw_text": "Signal B", "batch_id": "batch_1"},
        {"url": "https://c.com", "raw_text": "Signal C", "batch_id": "batch_1"},
    ]
    base_path = tmp_path / "base.csv"
    _write_csv(base_path, base_rows)
    out_path = tmp_path / "combined.csv"
    result = build_combined_input(
        base_path=str(base_path),
        targeted_path=None,
        validation_path=str(tmp_path / "empty_val.jsonl"),
        output_path=str(out_path),
    )
    assert result["base_rows"] == 3
    assert result["targeted_rows_included"] == 0
    assert result["combined_rows"] == 3
    with open(out_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 3


def test_valid_targeted_included(tmp_path):
    """Valid targeted signals are appended to base."""
    base_rows = [
        {"url": "https://a.com", "raw_text": "Signal A", "batch_id": "batch_1"},
    ]
    targeted_rows = [
        {"target_signal_id": "tsig_001", "url": "https://t1.com", "raw_text": "Targeted 1",
         "batch_id": "batch_stage33_targeted"},
        {"target_signal_id": "tsig_002", "url": "https://t2.com", "raw_text": "Targeted 2",
         "batch_id": "batch_stage33_targeted"},
    ]
    validations = [
        _make_validation("tsig_001", include=True),
        _make_validation("tsig_002", include=True),
    ]
    base_path = tmp_path / "base.csv"
    targeted_path = tmp_path / "targeted.csv"
    val_path = tmp_path / "val.jsonl"
    out_path = tmp_path / "combined.csv"
    _write_csv(base_path, base_rows)
    _write_csv(targeted_path, targeted_rows)
    _write_validations(val_path, validations)
    result = build_combined_input(
        base_path=str(base_path),
        targeted_path=str(targeted_path),
        validation_path=str(val_path),
        output_path=str(out_path),
    )
    assert result["base_rows"] == 1
    assert result["targeted_rows_included"] == 2
    assert result["combined_rows"] == 3


def test_invalid_targeted_excluded(tmp_path):
    """Invalid targeted signals are NOT included."""
    base_rows = [
        {"url": "https://a.com", "raw_text": "Signal A", "batch_id": "batch_1"},
    ]
    targeted_rows = [
        {"target_signal_id": "tsig_bad", "url": "", "raw_text": "",
         "batch_id": "batch_stage33_targeted"},
    ]
    validations = [
        _make_validation("tsig_bad", include=False, status="invalid"),
    ]
    base_path = tmp_path / "base.csv"
    targeted_path = tmp_path / "targeted.csv"
    val_path = tmp_path / "val.jsonl"
    out_path = tmp_path / "combined.csv"
    _write_csv(base_path, base_rows)
    _write_csv(targeted_path, targeted_rows)
    _write_validations(val_path, validations)
    result = build_combined_input(
        base_path=str(base_path),
        targeted_path=str(targeted_path),
        validation_path=str(val_path),
        output_path=str(out_path),
    )
    assert result["targeted_rows_included"] == 0
    assert result["combined_rows"] == 1


def test_duplicate_removed(tmp_path):
    """Duplicate url+text between base and targeted is deduplicated."""
    shared_url = "https://shared.com"
    shared_text = "Duplicate content here."
    base_rows = [
        {"url": shared_url, "raw_text": shared_text, "batch_id": "batch_1"},
    ]
    targeted_rows = [
        {"target_signal_id": "tsig_dup", "url": shared_url, "raw_text": shared_text,
         "batch_id": "batch_stage33_targeted"},
    ]
    validations = [_make_validation("tsig_dup", include=True)]
    base_path = tmp_path / "base.csv"
    targeted_path = tmp_path / "targeted.csv"
    val_path = tmp_path / "val.jsonl"
    out_path = tmp_path / "combined.csv"
    _write_csv(base_path, base_rows)
    _write_csv(targeted_path, targeted_rows)
    _write_validations(val_path, validations)
    result = build_combined_input(
        base_path=str(base_path),
        targeted_path=str(targeted_path),
        validation_path=str(val_path),
        output_path=str(out_path),
    )
    assert result["duplicates_removed"] == 1
    assert result["combined_rows"] == 1
