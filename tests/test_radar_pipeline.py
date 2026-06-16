"""Tests for radar pipeline."""
from __future__ import annotations
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from opc_foundation.sources.source_schema import FetchResult
from opc_foundation.run.time_utils import utcnow_iso
from demand_radar.acquisition.radar_pipeline import run_radar
import demand_radar.acquisition.acquisition_store as store_mod


def _mock_empty_fetch(source_id="src"):
    return FetchResult(source_id=source_id, connector="mock", raw_signals=[], fetched_at=utcnow_iso())


def _patch_store(tmp_path, monkeypatch):
    monkeypatch.setattr(store_mod, "_RAW_SIGNALS_PATH", tmp_path / "raw.jsonl")
    monkeypatch.setattr(store_mod, "_CANDIDATES_PATH", tmp_path / "cands.jsonl")
    monkeypatch.setattr(store_mod, "_RUN_LOG_PATH", tmp_path / "log.jsonl")


def test_run_radar_graceful_no_network(tmp_path, monkeypatch):
    _patch_store(tmp_path, monkeypatch)
    mock_connector = MagicMock()
    mock_connector.fetch.return_value = _mock_empty_fetch()

    with patch("demand_radar.acquisition.acquisition_pipeline._make_connector", return_value=mock_connector):
        result = run_radar(
            domain_id="ai_investment_tracking",
            draft_output=tmp_path / "draft.csv",
            radar_report_path=tmp_path / "radar_report.md",
            skip_r1_validation=True,
        )

    assert result.domain_id == "ai_investment_tracking"
    assert result.raw_signals >= 0


def test_run_radar_report_created(tmp_path, monkeypatch):
    _patch_store(tmp_path, monkeypatch)
    mock_connector = MagicMock()
    mock_connector.fetch.return_value = _mock_empty_fetch()

    with patch("demand_radar.acquisition.acquisition_pipeline._make_connector", return_value=mock_connector):
        run_radar(
            domain_id="ai_investment_tracking",
            draft_output=tmp_path / "draft.csv",
            radar_report_path=tmp_path / "radar_report.md",
            skip_r1_validation=True,
        )

    assert (tmp_path / "radar_report.md").exists()
    content = (tmp_path / "radar_report.md").read_text(encoding="utf-8")
    assert "ai_investment_tracking" in content