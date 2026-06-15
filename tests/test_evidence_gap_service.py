"""Tests for evidence_gap_service.py"""
from demand_radar.ui.evidence_gap_service import get_gap_analyses, get_collection_plans

def test_get_gap_analyses_empty(tmp_path, monkeypatch):
    import demand_radar.evidence_gap.evidence_gap_store as store
    monkeypatch.setattr(store, "GAP_PATH", tmp_path / "missing.jsonl")
    import demand_radar.ui.evidence_gap_service as svc
    monkeypatch.setattr(svc, "load_gap_analysis", lambda: [])
    result = get_gap_analyses()
    assert result == []

def test_get_collection_plans_empty(tmp_path, monkeypatch):
    import demand_radar.ui.evidence_gap_service as svc
    monkeypatch.setattr(svc, "load_collection_plans", lambda: [])
    result = get_collection_plans()
    assert result == []
