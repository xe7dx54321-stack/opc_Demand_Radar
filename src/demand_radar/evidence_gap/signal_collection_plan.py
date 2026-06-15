"""Generate TargetedSignalCollectionPlan from EvidenceGapAnalysis."""
from __future__ import annotations
from demand_radar.evidence_gap.evidence_gap_schema import (
    EvidenceGapAnalysis, TargetedSignalCollectionPlan,
)
from demand_radar.evidence_gap.evidence_gap_analyzer import _get_source_types
from demand_radar.state.raw_store import next_ids, utc_now_iso

_DOMAIN_KW_ZH = {
    "content_production": [
        "内容团队 选题 效率 痛点",
        "热点筛选 人工整理 素材 工作流",
        "自媒体 选题 工具 付费",
        "内容运营 信息源 分散",
        "AI 内容选题 工作流",
    ],
    "saas": [
        "SaaS 工具 信息整理 痛点",
        "企业知识库 检索 困难",
        "运营 文档分散 工作流",
    ],
    "investment": [
        "AI 项目初筛 信息分散 尽调",
        "投资人 AI 产业跟踪 数据源",
        "VC 项目筛选 人工整理 痛点",
        "AI 公司动态 追踪 工具 付费",
    ],
    "developer": [
        "开发者 API 文档 信息分散",
        "工具链 接入 调试 效率",
        "AI 智能体 工作流 中断",
    ],
}

_DOMAIN_KW_EN = {
    "content_production": [
        "content team topic research workflow pain",
        "editorial planning information overload",
        "content research tool pricing",
        "newsletter topic discovery workflow",
        "AI content planning workflow automation",
    ],
    "saas": [
        "enterprise knowledge base search difficulty",
        "SaaS tool information fragmentation pain",
        "operations workflow documentation scattered",
    ],
    "investment": [
        "AI startup deal sourcing research workflow",
        "VC AI market tracking pain point",
        "investor due diligence workflow tools",
        "AI company tracking tool pricing",
    ],
    "developer": [
        "developer API documentation fragmented debug",
        "AI agent workflow reliability issue",
        "tool chain integration pain point",
    ],
}

_POSITIVE_BY_MISSING = {
    "budget_signal": "明确语境包括预算、付费工具或采购记录",
    "paid_alternative": "提到使用付费工具或人力外包解决问题",
    "business_impact": "提到具体业务损失或错过机会的场景",
    "time_cost": "提到每天/每周花费多少小时处理这个问题",
    "frequency_signal": "该问题在多个帖子或回答中重复出现",
    "repeated_workflow": "描述日常工作流中重复遇到该问题",
    "source_diversity": "信号来自不同社区、平台或渠道",
    "manual_workaround": "描述具体的人工步骤或替代工具",
    "concrete_pain_quote": "包含具体场景和负面情绪的原始引用",
    "persona_specificity": "明确用户角色和责任范围",
    "current_solution": "提到当前使用的工具或流程",
    "stronger_pain_evidence": "包含强烈负面情绪或明确阔碍语境",
    "target_role_clarity": "明确提到具体职层或岗位名称",
    "urgency_signal": "表达紧迫性或需要立即解决的情绪",
}

_NEGATIVE_BY_MISSING = {
    "budget_signal": "没有任何成本或预算语境",
    "paid_alternative": "只说「这个问题很烦」但尚未尝试任何解决方法",
    "frequency_signal": "信号来自同一个人的多条帖子或单一事件记录",
    "persona_specificity": "用户角色模糊且无具体职能描述",
    "concrete_pain_quote": "标范化描述或和当前需求主题无关的一般性抱怊",
    "business_impact": "尚无明确业务损失，仅称该流程「不容易」",
    "source_diversity": "信号来源过于单一",
    "manual_workaround": "只表达不局服但未描述任何尝试方式",
    "current_solution": "无任何当前解决方案描述",
    "stronger_pain_evidence": "描述过于模糊，无具体痛点场景",
    "target_role_clarity": "用户角色不明确或过于泛泛",
    "urgency_signal": "无紧迫性信号，遇到问题但能接受",
    "time_cost": "没有提到时间成本或人力耗费",
}


def build_collection_plans(
    gap_analyses: list[EvidenceGapAnalysis],
) -> list[TargetedSignalCollectionPlan]:
    """Generate a TargetedSignalCollectionPlan for each EvidenceGapAnalysis."""
    ids = next_ids("signal_plan", [], len(gap_analyses))
    plans: list[TargetedSignalCollectionPlan] = []

    for plan_id, gap in zip(ids, gap_analyses):
        missing = gap.missing_evidence_types
        source_types = _get_source_types(missing)[:5]
        title_lower = gap.group_title_zh.lower()

        # Detect domain
        if any(kw in title_lower for kw in ["内容", "选题", "自媒体", "编辑"]):
            domain = "content_production"
        elif any(kw in title_lower for kw in ["投资", "vc", "尽调", "产业跟踪", "初筛"]):
            domain = "investment"
        elif any(kw in title_lower for kw in ["开发", "api", "工具链", "调试"]):
            domain = "developer"
        else:
            domain = "saas"

        kw_zh = list(_DOMAIN_KW_ZH.get(domain, _DOMAIN_KW_ZH["saas"]))
        kw_en = list(_DOMAIN_KW_EN.get(domain, _DOMAIN_KW_EN["saas"]))

        # Add missing-type specific keywords
        if "budget_signal" in missing or "paid_alternative" in missing:
            prefix = gap.group_title_zh[:8]
            kw_zh.append(prefix + " 付费 工具 抢占")
            kw_en.append("tool pricing subscription workflow")
        if "frequency_signal" in missing or "source_diversity" in missing:
            prefix = gap.group_title_zh[:8]
            kw_zh.append(prefix + " 重复 痛点 很多人")
            kw_en.append("common pain point repeated experience")
        if "business_impact" in missing:
            prefix = gap.group_title_zh[:8]
            kw_zh.append(prefix + " 业务损失 效率 影响")
            kw_en.append("business impact workflow inefficiency cost")

        positive = [
            _POSITIVE_BY_MISSING.get(m, "具体体现 " + m + " 的信号")
            for m in missing[:4]
        ]
        if not positive:
            positive = ["具体痛点场景，包含负面情绪表达"]

        negative = [
            _NEGATIVE_BY_MISSING.get(m, "没有体现真实 " + m + " 的信号")
            for m in missing[:3]
        ]
        if not negative:
            negative = ["标范化或模糊描述，无具体场景"]

        src_str = ", ".join(source_types[:3])
        missing_str = "、".join(missing[:3])
        notes = (
            "优先寻找以下类型信号："
            + missing_str + "。建议来源：" + src_str
            + "。目标数量：" + str(gap.target_new_signals) + " 条。"
        )
        new_score = min(gap.current_truth_score + 8, 75)
        impact = (
            "补充后预期分数可提升至 "
            + str(int(new_score)) + " 分，有望达到 strong 级别。"
        )

        plan = TargetedSignalCollectionPlan(
            plan_id=plan_id,
            gap_analysis_id=gap.gap_analysis_id,
            truth_score_id=gap.truth_score_id,
            source_group_id=gap.source_group_id,
            group_title_zh=gap.group_title_zh,
            target_new_signals=gap.target_new_signals,
            target_personas=[],
            target_source_types=source_types,
            target_languages=["zh", "en"],
            search_keywords_zh=kw_zh[:6],
            search_keywords_en=kw_en[:5],
            positive_signal_criteria=positive,
            negative_signal_criteria=negative,
            collection_notes_zh=notes,
            expected_impact_zh=impact,
            created_at=utc_now_iso(),
        )
        plans.append(plan)

    return plans
