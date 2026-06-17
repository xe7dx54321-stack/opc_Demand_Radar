"""UI service tests for D5 demand theme page."""
from __future__ import annotations

import json
from pathlib import Path

from demand_radar.ui.mvp_d_service import get_d5_demand_themes, get_d5_overview, get_d5_theme_review_queue


def test_ui_demand_themes_service_reads_theme_queue(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    Path("data/processed/d5").mkdir(parents=True)
    Path("outputs").mkdir(parents=True)
    theme = {
        "theme_id": "theme_000001",
        "theme_title_zh": "项目来源与筛选自动化",
        "action_recommendation": "watch",
        "confidence": 0.8,
    }
    queue = {
        "queue_item_id": "theme_queue_000001",
        "theme_id": "theme_000001",
        "priority": "medium",
    }
    Path("data/processed/d5/demand_themes.jsonl").write_text(json.dumps(theme, ensure_ascii=False) + "\n", encoding="utf-8")
    Path("data/processed/d5/theme_review_queue.jsonl").write_text(json.dumps(queue, ensure_ascii=False) + "\n", encoding="utf-8")
    Path("data/processed/d5/deduped_pain_items.jsonl").write_text('{"is_representative": true}\n', encoding="utf-8")
    Path("data/processed/d5/source_groups.jsonl").write_text('{"source_group_id": "source_group_000001"}\n', encoding="utf-8")
    Path("outputs/run_summary.json").write_text('{"d5_can_enter_theme_review": true}\n', encoding="utf-8")

    overview = get_d5_overview()

    assert get_d5_demand_themes()[0]["theme_title_zh"] == "项目来源与筛选自动化"
    assert get_d5_theme_review_queue()[0]["theme_id"] == "theme_000001"
    assert overview["themes"] == 1
    assert overview["watch"] == 1
    assert overview["can_enter_theme_review"] is True
