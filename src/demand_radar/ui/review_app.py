"""Streamlit app for local calibration review."""

from __future__ import annotations

import html
from typing import Iterable

import streamlit as st

from demand_radar.calibration.calibration_schema import VALID_REVIEW_LABELS
from demand_radar.reporting.calibration_report import build_calibration_report
from demand_radar.ui.review_service import (
    ReviewItem,
    add_review,
    evidence_quote_found,
    get_review_summary,
    load_review_items,
)


REVIEW_ACTIONS = [
    ("通过", "good_extraction"),
    ("较弱", "weak_extraction"),
    ("误报", "false_positive"),
    ("漏报", "false_negative"),
    ("引用问题", "bad_quote"),
    ("角色问题", "bad_persona"),
    ("痛点描述问题", "bad_pain_description"),
    ("缺付费信号", "missing_payment_signal"),
    ("缺替代方案", "missing_workaround"),
    ("应隔离", "should_quarantine"),
]

REVIEW_RANGES = [
    "All",
    "Unreviewed only",
    "Reviewed only",
    "Pain points only",
    "Quarantine only",
]

PERSONAS = [
    "All",
    "investor",
    "researcher",
    "founder",
    "content_team",
    "developer",
    "operator",
    "strategy_bd",
    "unknown",
]

RANGE_LABELS = {
    "All": "全部",
    "Unreviewed only": "仅未审核",
    "Reviewed only": "仅已审核",
    "Pain points only": "仅痛点",
    "Quarantine only": "仅隔离项",
}

REVIEW_LABELS = {
    "All": "全部",
    "good_extraction": "通过",
    "weak_extraction": "较弱",
    "false_positive": "误报",
    "false_negative": "漏报",
    "bad_quote": "引用问题",
    "bad_persona": "角色问题",
    "bad_pain_description": "痛点描述问题",
    "missing_workaround": "缺替代方案",
    "missing_payment_signal": "缺付费信号",
    "should_quarantine": "应隔离",
}

PERSONA_LABELS = {
    "All": "全部",
    "investor": "投资人",
    "researcher": "研究员",
    "founder": "创始人",
    "content_team": "内容团队",
    "developer": "开发者",
    "operator": "运营",
    "strategy_bd": "战略/BD",
    "unknown": "未知",
}

ITEM_TYPE_LABELS = {
    "pain_point": "痛点",
    "quarantine": "隔离项",
    "raw_only": "仅原始信号",
}

SOURCE_TYPE_LABELS = {
    "All": "全部",
    "manual": "手动",
    "forum_post": "论坛帖子",
    "api": "接口",
}

SOURCE_NAME_LABELS = {
    "manual_import": "手动导入",
}

LANGUAGE_LABELS = {
    "All": "全部",
    "en": "英文",
    "zh": "中文",
    "zh-CN": "中文",
    "zh_cn": "中文",
    "unknown": "未知",
}

DOMAIN_TAG_LABELS = {
    "ai_investment_research": "AI 投资研究",
    "ai_hardtech": "AI 硬科技",
    "content_production": "内容生产",
    "enterprise_knowledge_workflow": "企业知识工作流",
    "ai_agent_workflow": "AI Agent 工作流",
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


def main() -> None:
    st.set_page_config(page_title="需求雷达审核台", layout="wide")
    st.title("需求雷达审核台")
    st.caption(
        "本地校准审核界面。审核结果会作为反馈记忆追加保存，不会修改原始信号、"
        "标准化信号或已抽取痛点。"
    )

    items = load_review_items()
    summary = get_review_summary(items)
    _render_summary(summary)

    if st.button("重建校准报告", type="primary"):
        rebuilt = build_calibration_report()
        st.success(
            "校准报告已重建："
            f"审核记录 {rebuilt.calibration_reviews} 条，痛点 {rebuilt.pain_points} 条。"
        )

    filters = _sidebar_filters(items)
    filtered_items = _filter_items(items, filters)
    st.caption(f"当前显示 {len(filtered_items)} 条，共 {len(items)} 条审核项。")

    for item in filtered_items:
        _render_item(item)


def _render_summary(summary: object) -> None:
    labels = summary.labels
    metric_values = [
        ("原始信号", summary.raw_signals),
        ("标准化信号", summary.normalized_signals),
        ("痛点", summary.pain_points),
        ("隔离项", summary.quarantine),
        ("已审核", summary.reviewed),
        ("未审核", summary.unreviewed),
        ("通过", labels.get("good_extraction", 0)),
        ("较弱", labels.get("weak_extraction", 0)),
        ("误报", labels.get("false_positive", 0)),
        ("漏报", labels.get("false_negative", 0)),
        ("引用问题", labels.get("bad_quote", 0)),
        ("角色问题", labels.get("bad_persona", 0)),
        ("应隔离", labels.get("should_quarantine", 0)),
    ]
    columns = st.columns(7)
    for index, (label, value) in enumerate(metric_values):
        columns[index % len(columns)].metric(label, value)


def _sidebar_filters(items: list[ReviewItem]) -> dict[str, object]:
    with st.sidebar:
        st.header("筛选")
        review_range = st.radio("查看范围", REVIEW_RANGES, index=1, format_func=_range_label)
        label_options = ["All", *sorted(VALID_REVIEW_LABELS)]
        label = st.selectbox("审核标签", label_options, format_func=_review_label)
        persona = st.selectbox("用户角色", PERSONAS, format_func=_persona_label)
        source_types = ["All", *_unique_values(item.source_type for item in items)]
        source_type = st.selectbox("来源类型", source_types, format_func=_source_type_label)
        languages = ["All", *_unique_values(item.language for item in items)]
        language = st.selectbox("语言", languages, format_func=_language_label)
    return {
        "review_range": review_range,
        "label": label,
        "persona": persona,
        "source_type": source_type,
        "language": language,
    }


def _filter_items(items: list[ReviewItem], filters: dict[str, object]) -> list[ReviewItem]:
    result: list[ReviewItem] = []
    for item in items:
        review_range = filters["review_range"]
        if review_range == "Unreviewed only" and item.reviewed:
            continue
        if review_range == "Reviewed only" and not item.reviewed:
            continue
        if review_range == "Pain points only" and item.item_type != "pain_point":
            continue
        if review_range == "Quarantine only" and item.item_type != "quarantine":
            continue
        if filters["label"] != "All" and item.latest_review_label != filters["label"]:
            continue
        if filters["persona"] != "All":
            item_persona = item.persona or "unknown"
            if item_persona != filters["persona"]:
                continue
        if filters["source_type"] != "All" and item.source_type != filters["source_type"]:
            continue
        if filters["language"] != "All" and item.language != filters["language"]:
            continue
        result.append(item)
    return result


def _render_item(item: ReviewItem) -> None:
    title = f"{item.title} - {_item_type_label(item.item_type)}"
    with st.expander(title, expanded=not item.reviewed):
        _render_metadata(item)
        left, right = st.columns([3, 2])
        with left:
            st.subheader("信号文本")
            st.markdown("**原始文本**")
            st.text_area("原始文本", item.raw_text or "", height=140, label_visibility="collapsed", disabled=True)
            st.markdown("**标准化文本**")
            _render_normalized_text(item)
        with right:
            st.subheader("抽取结果")
            _render_extraction_fields(item)
            _render_review_status(item)
            _render_quarantine(item)
        _render_review_controls(item)


def _render_metadata(item: ReviewItem) -> None:
    metadata = [
        f"原始信号 ID：`{item.raw_signal_id}`",
        f"标准化信号 ID：`{item.normalized_signal_id or ''}`",
        f"痛点 ID：`{item.pain_point_id or ''}`",
        f"来源：`{_source_name_label(item.source_name or '')}` / `{_source_type_label(item.source_type or '')}`",
        f"语言：`{_language_label(item.language or '')}`",
        f"领域标签：`{_domain_tags_label(item.domain_tags)}`",
    ]
    st.markdown("  \n".join(metadata))
    if item.url:
        st.markdown(f"来源链接：[{item.url}]({item.url})")


def _render_normalized_text(item: ReviewItem) -> None:
    text = item.normalized_text or ""
    quote = (item.evidence_quote or "").strip()
    if quote and evidence_quote_found(item):
        st.markdown(_highlight_quote(text, quote), unsafe_allow_html=True)
    elif quote:
        st.warning("证据原文未在标准化文本中找到")
        st.text_area("标准化文本", text, height=180, label_visibility="collapsed", disabled=True)
    else:
        st.text_area("标准化文本", text, height=180, label_visibility="collapsed", disabled=True)


def _render_extraction_fields(item: ReviewItem) -> None:
    rows = [
        ("用户角色", _persona_label(item.persona or "")),
        ("场景", item.scenario),
        ("待完成任务", item.job_to_be_done),
        ("痛点", item.pain_description),
        ("当前替代方案", item.current_workaround),
        ("频率信号", item.frequency_signal),
        ("付费信号", item.payment_signal),
        ("置信度", f"{item.confidence:.2f}" if item.confidence is not None else None),
    ]
    for label, value in rows:
        st.markdown(f"**{label}:** {value or ''}")
    if item.evidence_quote:
        st.markdown("**证据原文：**")
        st.info(item.evidence_quote)


def _render_review_status(item: ReviewItem) -> None:
    if item.reviewed:
        st.success(f"已审核：{_review_label(item.latest_review_label or '')}")
        st.caption(item.latest_review_note or "")
    else:
        st.warning("未审核")


def _render_quarantine(item: ReviewItem) -> None:
    if item.item_type != "quarantine":
        return
    st.error(f"隔离原因：{_quarantine_reason_label(item.quarantine_reason or '')}")
    with st.expander("隔离原始载荷（保留原始字段）"):
        st.json(item.quarantine_payload or {})


def _render_review_controls(item: ReviewItem) -> None:
    key_base = _item_key(item)
    with st.form(f"review_form_{key_base}", clear_on_submit=False):
        note = st.text_area("审核备注", key=f"note_{key_base}")
        col_a, col_b, col_c = st.columns(3)
        expected_persona = col_a.text_input("期望用户角色", key=f"persona_{key_base}")
        expected_quote = col_b.text_input("期望证据原文", key=f"quote_{key_base}")
        expected_pain = col_c.text_input("期望痛点描述", key=f"pain_{key_base}")
        st.markdown("**审核动作**")
        button_columns = st.columns(5)
        submitted_label = None
        for index, (text, label) in enumerate(REVIEW_ACTIONS):
            if button_columns[index % len(button_columns)].form_submit_button(text):
                submitted_label = label
        if submitted_label:
            _save_review_from_form(
                item,
                submitted_label,
                note,
                expected_persona,
                expected_quote,
                expected_pain,
            )


def _save_review_from_form(
    item: ReviewItem,
    label: str,
    note: str,
    expected_persona: str,
    expected_quote: str,
    expected_pain: str,
) -> None:
    add_review(
        item,
        label=label,
        reviewer_note=note.strip() or f"标记为{_review_label(label)}",
        expected_persona=expected_persona.strip() or None,
        expected_evidence_quote=expected_quote.strip() or None,
        expected_pain_description=expected_pain.strip() or None,
        should_be_quarantined=True if label == "should_quarantine" else None,
    )
    st.success(f"已保存审核：{_review_label(label)}")
    st.rerun()


def _highlight_quote(text: str, quote: str) -> str:
    escaped_text = html.escape(text)
    escaped_quote = html.escape(quote)
    return escaped_text.replace(
        escaped_quote,
        f"<mark style='background:#fde68a;padding:0.08rem 0.2rem;border-radius:0.2rem'>{escaped_quote}</mark>",
        1,
    )


def _item_key(item: ReviewItem) -> str:
    return item.pain_point_id or item.normalized_signal_id or item.raw_signal_id


def _unique_values(values: Iterable[str | None]) -> list[str]:
    return sorted({value for value in values if value})


def _range_label(value: str) -> str:
    return RANGE_LABELS.get(value, value)


def _review_label(value: str) -> str:
    return REVIEW_LABELS.get(value, value)


def _persona_label(value: str) -> str:
    return PERSONA_LABELS.get(value, value or "未知")


def _item_type_label(value: str) -> str:
    return ITEM_TYPE_LABELS.get(value, value)


def _source_type_label(value: str) -> str:
    return SOURCE_TYPE_LABELS.get(value, value or "未知")


def _source_name_label(value: str) -> str:
    return SOURCE_NAME_LABELS.get(value, value or "未知")


def _language_label(value: str) -> str:
    return LANGUAGE_LABELS.get(value, value or "未知")


def _domain_tags_label(values: list[str]) -> str:
    if not values:
        return "无"
    return "，".join(DOMAIN_TAG_LABELS.get(value, value) for value in values)


def _quarantine_reason_label(value: str) -> str:
    return QUARANTINE_REASON_LABELS.get(value, value or "未知")


if __name__ == "__main__":
    main()
