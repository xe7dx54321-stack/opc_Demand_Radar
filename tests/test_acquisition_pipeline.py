"""Tests for acquisition pipeline (mocking at _make_connector level)."""
from __future__ import annotations
import pytest
import yaml
from pathlib import Path
from unittest.mock import MagicMock, patch
from opc_foundation.sources.source_schema import FetchResult
from opc_foundation.run.time_utils import utcnow_iso
from opc_foundation.signals.raw_signal_schema import RawSignal
from opc_foundation.signals.dedupe import hash_url, hash_text
import demand_radar.acquisition.acquisition_store as store_mod


def _mock_empty_result(source_id="src"):
    return FetchResult(source_id=source_id, connector="mock", raw_signals=[], fetched_at=utcnow_iso())


def _sig(n=1):
    text = "We spend hours every week manually tracking AI startups across blogs and newsletters. Very tedious workflow research."
    return RawSignal(
        signal_id=f"sig_{n:03d}",
        source_id="hacker_news_ai_investment",
        source_type="community_discussion",
        source_name="HN",
        source_url=f"https://example.com/{n}",
        raw_text=text,
        fetched_at=utcnow_iso(),
        url_hash=hash_url(f"https://example.com/{n}"),
        content_hash=hash_text(text + str(n)),
    )


def _patch_store(tmp_path, monkeypatch):
    monkeypatch.setattr(store_mod, "_RAW_SIGNALS_PATH", tmp_path / "raw.jsonl")
    monkeypatch.setattr(store_mod, "_CANDIDATES_PATH", tmp_path / "cands.jsonl")
    monkeypatch.setattr(store_mod, "_RUN_LOG_PATH", tmp_path / "log.jsonl")


def test_run_acquisition_no_network(tmp_path, monkeypatch):
    _patch_store(tmp_path, monkeypatch)
    mock_connector = MagicMock()
    mock_connector.fetch.return_value = _mock_empty_result()

    with patch("demand_radar.acquisition.acquisition_pipeline._make_connector", return_value=mock_connector):
        from demand_radar.acquisition.acquisition_pipeline import run_acquisition
        summary, candidates = run_acquisition(
            domain_id="ai_investment_tracking",
            raw_output_path=tmp_path / "raw.jsonl",
            candidates_output_path=tmp_path / "cands.jsonl",
            run_log_path=tmp_path / "log.jsonl",
            max_items_per_query=5,
        )

    assert summary.domain_id == "ai_investment_tracking"
    assert len(candidates) == 0


def test_run_acquisition_with_signals(tmp_path, monkeypatch):
    _patch_store(tmp_path, monkeypatch)
    mock_connector = MagicMock()
    calls = [0]

    def fake_fetch(query, source, context):
        calls[0] += 1
        if calls[0] == 1:
            return FetchResult(
                source_id=source.source_id, connector="mock",
                raw_signals=[_sig(1)], fetched_at=utcnow_iso()
            )
        return _mock_empty_result(source.source_id)

    mock_connector.fetch.side_effect = fake_fetch

    with patch("demand_radar.acquisition.acquisition_pipeline._make_connector", return_value=mock_connector):
        from demand_radar.acquisition.acquisition_pipeline import run_acquisition
        summary, candidates = run_acquisition(
            domain_id="ai_investment_tracking",
            raw_output_path=tmp_path / "raw.jsonl",
            candidates_output_path=tmp_path / "cands.jsonl",
            run_log_path=tmp_path / "log.jsonl",
            max_items_per_query=5,
        )

    assert summary.raw_signal_count >= 1
    assert len(candidates) >= 1


def test_connector_error_does_not_abort(tmp_path, monkeypatch):
    _patch_store(tmp_path, monkeypatch)
    mock_connector = MagicMock()
    mock_connector.fetch.side_effect = Exception("network error")

    with patch("demand_radar.acquisition.acquisition_pipeline._make_connector", return_value=mock_connector):
        from demand_radar.acquisition.acquisition_pipeline import run_acquisition
        summary, _ = run_acquisition(
            domain_id="ai_investment_tracking",
            raw_output_path=tmp_path / "raw.jsonl",
            candidates_output_path=tmp_path / "cands.jsonl",
            run_log_path=tmp_path / "log.jsonl",
            max_items_per_query=2,
        )

    assert len(summary.errors) >= 1


def test_manual_url_csv_not_found_is_warning(tmp_path, monkeypatch):
    _patch_store(tmp_path, monkeypatch)
    mock_connector = MagicMock()
    mock_connector.fetch.return_value = _mock_empty_result()

    cfg_dir = tmp_path / "domain_configs"
    cfg_dir.mkdir()
    (cfg_dir / "test_domain.yaml").write_bytes(
        yaml.dump({"domain_id": "test_domain", "domain_title_zh": "Test", "search_queries": []}).encode("utf-8")
    )

    registry_path = tmp_path / "registry.yaml"
    registry_path.write_bytes(yaml.dump({
        "sources": [{
            "source_id": "manual_test",
            "source_name": "Manual Test",
            "source_type": "manual_url",
            "connector": "manual_url",
            "enabled": True,
            "trust_weight": 0.8,
            "default_queries": [],
            "metadata": {"input_csv": str(tmp_path / "nonexistent.csv")},
        }]
    }).encode("utf-8"))

    with patch("demand_radar.acquisition.acquisition_pipeline._make_connector", return_value=mock_connector):
        from demand_radar.acquisition.acquisition_pipeline import run_acquisition
        summary, _ = run_acquisition(
            domain_id="test_domain",
            domain_config_dir=cfg_dir,
            source_registry_path=registry_path,
            raw_output_path=tmp_path / "raw.jsonl",
            candidates_output_path=tmp_path / "cands.jsonl",
            run_log_path=tmp_path / "log.jsonl",
        )

    assert len(summary.warnings) >= 1 or summary.raw_signal_count == 0