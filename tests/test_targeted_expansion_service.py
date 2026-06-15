"""Tests for Stage 3.3 targeted_expansion_service."""
import json
import pytest
from pathlib import Path
from datetime import datetime, timezone


def _now():
    return datetime.now(timezone.utc).isoformat()


def test_get_expansion_summary_no_file(tmp_path, monkeypatch):
    import demand_radar.targeted_expansion.expansion_store as store_mod
    monkeypatch.setattr(store_mod, "SUMMARY_PATH", tmp_path / "no_summary.json")
    from demand_radar.ui.targeted_expansion_service import get_expansion_summary
    result = get_expansion_summary()
    assert result is None


def test_get_expansion_summary_with_file(tmp_path, monkeypatch):
    import demand_radar.targeted_expansion.expansion_store as store_mod
    summary_path = tmp_path / "summary.json"
    data = {
        "template_rows": 40,
        "filled_signals": 35,
        "valid_signals": 30,
        "warning_signals": 3,
        "invalid_signals": 2,
        "excluded_synthetic": 0,
        "combined_input_rows": 110,
        "base_rows": 80,
        "targeted_rows_included": 30,
        "duplicates_removed": 0,
        "created_at": _now(),
    }
    summary_path.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(store_mod, "SUMMARY_PATH", summary_path)
    from demand_radar.ui.targeted_expansion_service import get_expansion_summary
    result = get_expansion_summary()
    assert result is not None
    assert result.template_rows == 40
    assert result.valid_signals == 30


def test_get_targeted_validations_empty(tmp_path, monkeypatch):
    import demand_radar.targeted_expansion.targeted_validator as val_mod
    monkeypatch.setattr(val_mod, "Path", lambda p: tmp_path / "empty.jsonl" if "targeted_signal_validation" in str(p) else Path(p))
    from demand_radar.ui.targeted_expansion_service import get_targeted_validations
    # With non-existent file
    from demand_radar.targeted_expansion.targeted_validator import load_validations
    result = load_validations(str(tmp_path / "nonexistent.jsonl"))
    assert result == []


def test_get_truth_score_deltas_empty(tmp_path, monkeypatch):
    import demand_radar.targeted_expansion.expansion_store as store_mod
    monkeypatch.setattr(store_mod, "DELTA_PATH", tmp_path / "no_deltas.jsonl")
    from demand_radar.ui.targeted_expansion_service import get_truth_score_deltas
    result = get_truth_score_deltas()
    assert result == []


def test_get_truth_score_deltas_with_data(tmp_path, monkeypatch):
    import demand_radar.targeted_expansion.expansion_store as store_mod
    from demand_radar.targeted_expansion.targeted_schema import TruthScoreDelta
    delta = TruthScoreDelta(
        source_group_id="grp_001",
        group_title_zh="测试候选",
        before_truth_score=60.0,
        after_truth_score=72.0,
        delta=12.0,
        before_truth_level="medium",
        after_truth_level="medium",
        created_at=_now(),
    )
    delta_path = tmp_path / "deltas.jsonl"
    delta_path.write_text(delta.model_dump_json() + "\n", encoding="utf-8")
    monkeypatch.setattr(store_mod, "DELTA_PATH", delta_path)
    from demand_radar.ui.targeted_expansion_service import get_truth_score_deltas
    result = get_truth_score_deltas()
    assert len(result) == 1
    assert result[0].delta == pytest.approx(12.0)
