"""Chinese labels for the D4 review console.

The D4 review files keep machine-readable enum values such as ``strong`` and
``pursue``. The Streamlit UI should show Chinese labels while preserving those
raw values for storage and compatibility.
"""

from __future__ import annotations

from typing import Any


STRENGTH_LABELS = {
    "strong": "强证据",
    "medium": "中证据",
    "weak": "弱证据",
    "fake_or_insufficient": "伪证据或证据不足",
    "reject": "不抽取",
}

COMMERCIAL_LABELS = {
    "high": "高商业潜力",
    "medium": "中商业潜力",
    "low": "低商业潜力",
    "unclear": "商业潜力不明确",
}

ACTION_LABELS = {
    "pursue": "继续推进",
    "watch": "观察",
    "reject": "拒绝",
    "needs_more_evidence": "需要更多证据",
}

EXTRACTION_LABELS = {
    "good": "抽取质量好",
    "partial": "抽取部分正确",
    "bad": "抽取质量差",
}

ERROR_LABELS = {
    "bad_persona": "用户角色不准",
    "bad_workflow": "工作流不准",
    "bad_pain_type": "痛点类型不准",
    "bad_quote": "证据引用不准",
    "hallucinated_field": "字段存在幻觉",
    "missed_commercial_signal": "遗漏商业信号",
    "domain_out": "领域不相关",
    "duplicate": "重复信号",
    "too_generic": "过于泛泛",
    "source_too_weak": "来源证据太弱",
}

QUERY_TYPE_LABELS = {
    "pain_phrase": "痛点表达",
    "complaint_phrase": "吐槽表达",
    "workaround_phrase": "替代方案表达",
    "job_to_be_done": "任务意图",
    "manual_workflow": "人工工作流",
    "spreadsheet_workaround": "表格替代方案",
    "alternative_tool": "替代工具",
    "buying_intent": "购买意图",
    "competitor_review": "竞品评价",
    "community_question": "社区提问",
    "foundation_search": "Foundation 搜索",
    "?": "未知查询类型",
    "unknown": "未知查询类型",
}

SOURCE_TYPE_LABELS = {
    "web_search": "网页搜索",
    "web_page": "网页",
    "rss": "RSS",
    "hacker_news": "Hacker News",
    "github_issue": "GitHub Issue",
    "manual_url": "手动 URL",
}

RAW_TEXT_SOURCE_LABELS = {
    "full_page": "完整页面正文",
    "snippet": "搜索摘要",
    "search_result": "搜索结果摘要",
    "raw_text": "原始文本",
}

WORKFLOW_LABELS = {
    "research_execution": "研究执行",
    "earnings research & analysis": "财报研究与分析",
    "deal sourcing / pipeline management": "项目发现与管线管理",
    "deal sourcing / initial screening": "项目发现与初筛",
    "deal sourcing & target identification": "项目发现与目标识别",
    "market research & competitive analysis": "市场研究与竞争分析",
    "research & screening": "研究与筛选",
    "deal flow management & due diligence": "项目流管理与尽调",
    "data_gathering_and_analysis": "数据收集与分析",
    "research_and_screening": "研究与筛选",
    "data_collection_and_analysis": "数据收集与分析",
    "research execution & coverage scaling": "研究执行与覆盖扩展",
    "financial modeling & research": "财务建模与研究",
    "screening & deep research": "筛选与深度研究",
    "financial modeling & research execution": "财务建模与研究执行",
    "market research & startup scouting": "市场研究与创业项目发现",
    "competitive analysis / market research": "竞争分析与市场研究",
    "deal flow screening & due diligence": "项目流筛选与尽调",
    "data gathering & document analysis": "数据收集与文档分析",
    "research_report_generation": "研究报告生成",
    "market research & deal sourcing": "市场研究与项目发现",
    "deal sourcing & screening": "项目发现与筛选",
}

PAIN_TYPE_LABELS = {
    "workflow_inefficiency": "工作流效率低",
    "workflow_overload": "工作流负载过高",
    "workflow_fragmentation": "工作流碎片化",
    "manual_process": "依赖手工流程",
    "time_cost": "时间成本高",
    "information overload + process inefficiency": "信息过载与流程低效",
    "workflow_inefficiency + tool_fragmentation": "工作流低效与工具碎片化",
    "skill gap / workflow capability gap": "能力缺口与工作流能力缺口",
    "skill gap / workflow complexity": "能力缺口与工作流复杂度高",
}

COMMERCIAL_SIGNAL_LABELS = {
    "workflow_automation_demand": "工作流自动化需求",
    "tool_adoption": "工具采用信号",
    "workflow_tool_adoption": "工作流工具采用",
    "tool_seeking": "正在寻找工具",
    "hiring_signal": "招聘需求信号",
    "pain_driven_adoption": "痛点驱动的采用",
    "workflow_tool_need": "工作流工具需求",
    "workflow_tool_demand": "工作流工具需求",
    "tool_consolidation_demand": "工具整合需求",
    "tool_adoption_pain": "工具采用痛点",
    "workflow_pain": "工作流痛点",
    "workflow_automation_template": "工作流自动化模板需求",
    "workflow_upgrade_intent": "工作流升级意图",
    "workflow_automation": "工作流自动化",
    "workflow_template": "工作流模板需求",
    "tool_adoption_signal": "工具采用信号",
    "talent demand / skill development need": "人才需求与技能提升需求",
    "workflow_upgrade_demand": "工作流升级需求",
    "pain_point": "痛点信号",
    "talent_demand": "人才需求",
}

METRIC_LABELS = {
    "selected_queries": "已选择查询",
    "search_results": "搜索结果",
    "unique_urls": "去重 URL",
    "gate_allowed": "闸门通过",
    "selected_for_llm": "送入大模型",
    "should_extract_true": "可审核痛点",
    "yield_rate": "证据产出率",
}

PRIORITY_LABELS = {
    "high": "高",
    "medium": "中",
    "low": "低",
}

TRUTH_LEVEL_LABELS = {
    "strong": "强",
    "medium": "中",
    "weak": "弱",
    "insufficient": "不足",
}

NEXT_ACTION_LABELS = {
    "proceed_to_fit_scoring": "可进入适配度评分",
    "needs_more_evidence": "需要更多证据",
    "keep_watch": "持续观察",
    "discard": "建议丢弃",
    "pursue": "继续推进",
    "watch": "观察",
    "reject": "拒绝",
}

SOURCE_STRATEGY_LABELS = {
    "keep": "保留",
    "deprioritize": "降低优先级",
    "use_only_for_context": "仅用于背景信息",
    "needs_better_query": "需要更好的查询",
    "needs_new_connector": "需要新来源验证",
}

SOURCE_CATEGORY_LABELS = {
    "user_discussion": "用户讨论",
    "product_review": "产品评价",
    "workaround_discussion": "替代方案讨论",
    "community_question": "社区提问",
    "comparison_page": "对比页面",
    "practitioner_blog": "从业者博客",
    "job_description": "招聘描述",
    "unknown": "未知来源类别",
}


def label_value(value: Any, labels: dict[str, str], empty: str = "未标注") -> str:
    raw = "" if value is None else str(value).strip()
    if not raw:
        return empty
    return labels.get(raw, raw)


def strength_label(value: Any) -> str:
    return label_value(value, STRENGTH_LABELS, "未知强度")


def commercial_label(value: Any) -> str:
    return label_value(value, COMMERCIAL_LABELS, "未判断")


def action_label(value: Any) -> str:
    return label_value(value, ACTION_LABELS, "未决策")


def extraction_label(value: Any) -> str:
    return label_value(value, EXTRACTION_LABELS, "未判断")


def error_label(value: Any) -> str:
    return label_value(value, ERROR_LABELS, "未标注")


def query_type_label(value: Any) -> str:
    return label_value(value, QUERY_TYPE_LABELS, "未知查询类型")


def source_type_label(value: Any) -> str:
    return label_value(value, SOURCE_TYPE_LABELS, "未知来源")


def raw_text_source_label(value: Any) -> str:
    return label_value(value, RAW_TEXT_SOURCE_LABELS, "未标注")


def workflow_label(value: Any) -> str:
    return label_value(value, WORKFLOW_LABELS, "未标注")


def pain_type_label(value: Any) -> str:
    return label_value(value, PAIN_TYPE_LABELS, "未标注")


def commercial_signal_label(value: Any) -> str:
    return label_value(value, COMMERCIAL_SIGNAL_LABELS, "未标注")


def metric_label(value: Any) -> str:
    return label_value(value, METRIC_LABELS, "未知指标")


def priority_label(value: Any) -> str:
    return label_value(value, PRIORITY_LABELS, "未知优先级")


def truth_level_label(value: Any) -> str:
    return label_value(value, TRUTH_LEVEL_LABELS, "未知等级")


def next_action_label(value: Any) -> str:
    return label_value(value, NEXT_ACTION_LABELS, "未知动作")


def source_strategy_label(value: Any) -> str:
    return label_value(value, SOURCE_STRATEGY_LABELS, "未知策略")


def source_category_label(value: Any) -> str:
    return label_value(value, SOURCE_CATEGORY_LABELS, "未知来源类别")


def d4_card_title(item: dict[str, Any], max_chars: int = 86) -> str:
    """Prefer Chinese pain text for the visible card title."""
    for key in ("pain_description_zh", "job_to_be_done", "reasoning_summary_zh"):
        value = str(item.get(key) or "").strip()
        if value:
            return value if len(value) <= max_chars else value[: max_chars - 1] + "..."

    fallback = str(item.get("pain_item_id") or item.get("candidate_id") or "未命名痛点")
    return fallback if len(fallback) <= max_chars else fallback[: max_chars - 1] + "..."
