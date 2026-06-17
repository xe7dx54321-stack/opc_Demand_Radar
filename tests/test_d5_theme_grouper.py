"""D5 theme grouper tests."""
from __future__ import annotations

from pathlib import Path

from demand_radar.d5.pain_deduper import dedupe_pain_items
from demand_radar.d5.theme_grouper import build_demand_themes

from tests.test_d5_fixtures import pain_row, review_row, write_config, write_jsonl


def test_theme_grouping_merges_same_workflow_and_pain_type(tmp_path: Path) -> None:
    pain_path = tmp_path / "pain.jsonl"
    reviews_path = tmp_path / "reviews.jsonl"
    write_jsonl(
        pain_path,
        [
            pain_row("pain__001", "https://www.reddit.com/r/vc/a", workflow_stage="deal sourcing"),
            pain_row("pain__002", "https://forum.example/b", workflow_stage="deal sourcing"),
            pain_row("pain__003", "https://blog.example/c", workflow_stage="deal sourcing"),
            pain_row("pain__004", "https://research.example/d", workflow_stage="market research"),
        ],
    )
    write_jsonl(reviews_path, [review_row("pain__001", action_decision="pursue")])
    config = write_config(tmp_path, pain_path, reviews_path)
    dedupe_pain_items(config_path=config)

    themes = build_demand_themes(config_path=config)

    workflows = {theme.workflow_group: theme for theme in themes}
    assert "项目来源与筛选" in workflows
    assert workflows["项目来源与筛选"].evidence_count == 3
    assert workflows["项目来源与筛选"].action_recommendation == "pursue_candidate"
    assert "市场研究与竞争分析" in workflows


def test_same_pain_type_different_workflow_not_force_merged(tmp_path: Path) -> None:
    pain_path = tmp_path / "pain.jsonl"
    reviews_path = tmp_path / "reviews.jsonl"
    write_jsonl(
        pain_path,
        [
            pain_row("pain__001", "https://a.example/1", workflow_stage="deal sourcing", pain_type="manual_workflow"),
            pain_row("pain__002", "https://b.example/2", workflow_stage="market research", pain_type="manual_workflow"),
        ],
    )
    write_jsonl(reviews_path, [])
    config = write_config(tmp_path, pain_path, reviews_path)
    dedupe_pain_items(config_path=config)

    themes = build_demand_themes(config_path=config)

    assert len(themes) == 2
