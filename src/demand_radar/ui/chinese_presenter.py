"""Chinese presentation helpers for the local review UI.

The review UI is for human calibration, not for preserving source text. Raw
English evidence stays in JSONL state and source links; this module builds a
clean Chinese-facing view for reviewers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ChineseReviewView:
    title: str
    summary: str
    scenario: str
    job_to_be_done: str
    pain_description: str
    current_workaround: str
    frequency_signal: str
    payment_signal: str
    evidence_summary: str


PERSONA_LABELS = {
    "investor": "投资人",
    "researcher": "研究员",
    "founder": "创始人",
    "content_team": "内容团队",
    "developer": "开发者",
    "operator": "运营",
    "strategy_bd": "战略与商务拓展",
    "unknown": "未知用户",
}

DOMAIN_LABELS = {
    "ai_investment_research": "人工智能投资研究",
    "ai_hardtech": "人工智能硬科技",
    "content_production": "内容生产",
    "enterprise_knowledge_workflow": "企业知识工作流",
    "ai_agent_workflow": "人工智能智能体工作流",
}

QUARANTINE_REASON_LABELS = {
    "schema_invalid": "结构校验失败",
    "missing_evidence_quote": "缺少证据原文",
    "evidence_quote_not_found": "证据原文未在文本中找到",
    "low_confidence": "置信度过低",
    "empty_text": "文本为空",
    "duplicate_signal": "重复信号",
    "extractor_error": "抽取器异常",
}

SHORT_PHRASE_LABELS = {
    "weekly": "每周",
    "daily": "每天",
    "monthly": "每月",
    "manual": "人工处理",
    "manual spreadsheet": "手工表格",
    "manual search": "人工搜索",
    "paid databases": "付费数据库",
    "api": "接口",
    "sdk": "开发工具包",
    "developer api pain": "开发者接口使用痛点",
    "tracking ai infrastructure companies": "追踪人工智能基础设施公司",
    "tracking ai infrastructure": "追踪人工智能基础设施",
    "monitor company and technical updates": "监控公司与技术动态",
    "monitor company/product/financing updates": "监控公司、产品与融资动态",
    "complete developer workflow with less friction": "更顺畅地完成开发流程",
}

KNOWN_ENGLISH_SUMMARIES = [
    (
        ("tracking ai infrastructure", "paid databases"),
        "投资团队每周要追踪人工智能基础设施公司的动态，但信息分散在多类渠道中；付费数据库也会漏掉技术更新，团队只能维护手工表格。",
    ),
    (
        ("ai agents", "customer research", "manual checking"),
        "创业团队尝试用人工智能智能体做客户研究，但流程交接不可靠，每一步仍要人工复核，创始人无法信任最终摘要。",
    ),
    (
        ("weekly newsletter", "no good way to summarize"),
        "内容创作者在写周报前，需要花大量时间比较产品发布、融资新闻和创始人动态，缺少可靠方式总结变化。",
    ),
    (
        ("api examples", "sdk docs"),
        "开发者难以快速找到合适的接口示例，问题讨论中的临时方案分散，开发工具包文档不完整且检索慢。",
    ),
    (
        ("verify ai vendor claims", "benchmarks"),
        "研究员难以验证人工智能供应商的宣称，因为基准测试、客户案例和定价信息分散在多个页面。",
    ),
    (
        ("sop", "slack", "wastes time"),
        "运营团队面对标准作业流程变更时，被大量讨论消息淹没，需要手动核对文档和旧工单，每周都浪费时间。",
    ),
    (
        ("dashboards are useful", "someday"),
        "这条信号只是模糊提到想看市场更新，没有描述明确、正在发生的痛点。",
    ),
    (
        ("shipped", "new ai notes feature"),
        "这条材料更像产品功能发布，没有呈现明确的用户痛点。",
    ),
    (
        ("will probably transform", "next decade"),
        "这条材料是趋势观点，没有具体需求、场景或替代方案。",
    ),
    (
        ("crm lead research", "sales reps"),
        "商务拓展和销售团队做线索研究时噪音太多，触达前仍要人工核对网站动态、社交动态和融资新闻。",
    ),
]

PAIN_SIGNAL_LABELS = [
    ("scattered across", "信息分散"),
    ("scattered", "信息分散"),
    ("manual process", "流程依赖人工"),
    ("manual", "需要人工处理"),
    ("miss important updates", "容易遗漏重要更新"),
    ("miss", "容易遗漏"),
    ("incomplete", "资料不完整"),
    ("slow", "检索或处理速度慢"),
    ("too much time", "耗时过多"),
    ("waste time", "浪费时间"),
    ("hard to verify", "验证困难"),
    ("hard to track", "追踪困难"),
    ("hard to compare", "比较困难"),
    ("hard to summarize", "总结困难"),
    ("hard to find", "查找困难"),
    ("struggle", "推进困难"),
    ("not reliable", "流程不可靠"),
    ("cannot trust", "结果不可信"),
    ("too noisy", "噪音过多"),
    ("no good way", "缺少好办法"),
    ("workaround", "依赖临时方案"),
    ("expensive", "成本偏高"),
]


def build_chinese_review_view(item: Any) -> ChineseReviewView:
    """Build a Chinese-only presentation view from a review item."""

    source_blob = _source_blob(item)
    pain_description = _to_chinese(getattr(item, "pain_description", None), item) or _to_chinese(source_blob, item)
    scenario = _to_chinese(getattr(item, "scenario", None), item) or _default_scenario(item)
    job_to_be_done = _to_chinese(getattr(item, "job_to_be_done", None), item) or _default_job(item)
    current_workaround = _to_chinese(getattr(item, "current_workaround", None), item) or _default_workaround(source_blob)
    frequency_signal = _to_chinese(getattr(item, "frequency_signal", None), item)
    payment_signal = _to_chinese(getattr(item, "payment_signal", None), item)
    evidence_summary = _to_chinese(getattr(item, "evidence_quote", None), item) or _to_chinese(source_blob, item)

    if getattr(item, "item_type", "") == "quarantine":
        reason = _quarantine_reason_label(getattr(item, "quarantine_reason", "") or "")
        title = f"隔离项：{reason}"
        summary = f"这条信号暂未进入有效痛点列表，隔离原因是：{reason}。建议只通过来源链接复核原文。"
    elif getattr(item, "item_type", "") == "raw_only":
        title = f"未抽取痛点：{_domain_label(item)}"
        summary = "这条信号暂未形成有效痛点。建议确认是否确实没有明确需求，或是否属于漏抽。"
    else:
        title = _title_from_signals(item, source_blob)
        summary = _summary_sentence(item, pain_description, scenario, current_workaround)

    return ChineseReviewView(
        title=_truncate(title, 52),
        summary=summary,
        scenario=scenario,
        job_to_be_done=job_to_be_done,
        pain_description=pain_description,
        current_workaround=current_workaround,
        frequency_signal=frequency_signal,
        payment_signal=payment_signal,
        evidence_summary=evidence_summary,
    )


def looks_like_english(text: str | None) -> bool:
    if not text:
        return False
    ascii_letters = sum(1 for char in text if char.isascii() and char.isalpha())
    cjk_chars = sum(1 for char in text if "\u4e00" <= char <= "\u9fff")
    if cjk_chars == 0 and ascii_letters >= 3:
        return True
    return ascii_letters >= 20 and ascii_letters > cjk_chars * 2


def _to_chinese(text: str | None, item: Any) -> str:
    value = (text or "").strip()
    if not value:
        return ""
    exact = SHORT_PHRASE_LABELS.get(value.lower())
    if exact:
        return exact
    if not looks_like_english(value):
        return _replace_embedded_terms(value)
    known = _known_english_summary(value)
    if known:
        return known
    return _heuristic_summary(value, item)


def _replace_embedded_terms(text: str) -> str:
    replacements = {
        "AI Agent": "人工智能智能体",
        "AI agent": "人工智能智能体",
        "AI": "人工智能",
        "API": "接口",
        "SDK": "开发工具包",
        "BD": "商务拓展",
        "GitHub": "代码托管平台",
        "CRM": "客户关系管理系统",
        "SOP": "标准作业流程",
        "FAQ": "常见问题",
    }
    result = text
    for source, target in replacements.items():
        result = result.replace(source, target)
    return result


def _known_english_summary(text: str) -> str:
    lower = text.lower()
    for keywords, summary in KNOWN_ENGLISH_SUMMARIES:
        if all(keyword in lower for keyword in keywords):
            return summary
    return ""


def _heuristic_summary(text: str, item: Any) -> str:
    lower = text.lower()
    signals: list[str] = []
    for keyword, label in PAIN_SIGNAL_LABELS:
        if keyword in lower and label not in signals:
            signals.append(label)
    if not signals:
        return "这条材料没有呈现明确、可验证的需求痛点。"
    signal_text = "、".join(signals[:4])
    return f"{_persona_label(item)}在{_domain_label(item)}相关工作中遇到{signal_text}的问题，需要进一步人工复核。"


def _title_from_signals(item: Any, source_blob: str) -> str:
    summary = _to_chinese(source_blob, item)
    if "没有呈现明确" in summary or "没有具体需求" in summary or "功能发布" in summary:
        return f"弱信号：{_domain_label(item)}"
    signals = _extract_signal_labels(source_blob)
    if signals:
        return f"{_persona_label(item)}：{'、'.join(signals[:2])}"
    return f"{_persona_label(item)}的{_domain_label(item)}需求"


def _extract_signal_labels(text: str) -> list[str]:
    lower = text.lower()
    labels: list[str] = []
    for keyword, label in PAIN_SIGNAL_LABELS:
        if keyword in lower and label not in labels:
            labels.append(label)
    return labels


def _summary_sentence(item: Any, pain_description: str, scenario: str, current_workaround: str) -> str:
    persona = _persona_label(item)
    if "没有呈现明确" in pain_description or "没有具体需求" in pain_description:
        return pain_description
    parts = [f"{persona}在{scenario}中，主要痛点是：{pain_description}"]
    if current_workaround:
        parts.append(f"当前做法是：{current_workaround}")
    return "；".join(parts) + "。"


def _default_scenario(item: Any) -> str:
    return f"{_domain_label(item)}相关工作流"


def _default_job(item: Any) -> str:
    return f"更稳定地完成{_domain_label(item)}相关判断和交付"


def _default_workaround(source_blob: str) -> str:
    signals = _extract_signal_labels(source_blob)
    if "需要人工处理" in signals or "流程依赖人工" in signals:
        return "依靠人工搜索、核对、整理和复盘"
    return ""


def _persona_label(item: Any) -> str:
    persona = getattr(item, "persona", None) or "unknown"
    return PERSONA_LABELS.get(persona, "未知用户")


def _domain_label(item: Any) -> str:
    tags = getattr(item, "domain_tags", None) or []
    if not tags:
        return "未标注领域"
    return DOMAIN_LABELS.get(tags[0], tags[0])


def _quarantine_reason_label(value: str) -> str:
    return QUARANTINE_REASON_LABELS.get(value, value or "未知原因")


def _source_blob(item: Any) -> str:
    parts = [
        getattr(item, "title", "") or "",
        getattr(item, "pain_description", "") or "",
        getattr(item, "scenario", "") or "",
        getattr(item, "job_to_be_done", "") or "",
        getattr(item, "current_workaround", "") or "",
        getattr(item, "evidence_quote", "") or "",
        getattr(item, "normalized_text", "") or "",
        getattr(item, "raw_text", "") or "",
    ]
    return " ".join(part for part in parts if part)


def _truncate(text: str, max_chars: int) -> str:
    return text if len(text) <= max_chars else f"{text[: max_chars - 1]}…"
