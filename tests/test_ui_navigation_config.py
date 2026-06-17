"""Navigation config tests for consolidated Review Console."""

from demand_radar.ui.navigation_config import HISTORY_PAGES, NAV_TABS


def test_top_level_navigation_has_current_workbench_entries_only() -> None:
    assert NAV_TABS == [
        "当前任务",
        "待审核队列",
        "需求证据结果",
        "诊断与历史",
        "设置与运行状态",
    ]
    assert len(NAV_TABS) <= 5
    assert "MVP-D4 Foundation搜索" not in NAV_TABS
    assert "MVP-C 人工校准" not in NAV_TABS


def test_history_archive_keeps_legacy_stage_entries() -> None:
    labels = [label for label, _ in HISTORY_PAGES]

    assert any("MVP-C" in label for label in labels)
    assert any("MVP-D4" in label for label in labels)
    assert any("批次总览" in label for label in labels)
