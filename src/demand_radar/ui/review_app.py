"""Streamlit app for local calibration review."""

from __future__ import annotations

from typing import Iterable

import streamlit as st

from demand_radar.calibration.calibration_schema import VALID_REVIEW_LABELS
from demand_radar.clustering.cluster_report import build_cluster_report
from demand_radar.clustering.merge_report import build_merge_report, build_reviewed_groups_report
from demand_radar.clustering.merge_store import build_reviewed_cluster_groups
from demand_radar.reporting.calibration_report import build_calibration_report
from demand_radar.ui.cluster_review_service import (
    ClusterReviewItem,
    add_cluster_review,
    get_cluster_review_summary,
    load_cluster_review_items,
)
from demand_radar.ui.chinese_presenter import build_chinese_review_view, looks_like_english
from demand_radar.ui.merge_review_service import (
    MergeReviewItem,
    add_merge_review,
    get_merge_review_summary,
    load_merge_review_items,
)
from demand_radar.ui.review_service import (
    ReviewItem,
    add_review,
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

CLUSTER_REVIEW_ACTIONS = [
    ("通过", "good_cluster"),
    ("过宽", "too_broad"),
    ("过窄", "too_narrow"),
    ("分组错误", "wrong_grouping"),
    ("重复主题", "duplicate_cluster"),
    ("标题问题", "bad_title"),
    ("应合并", "should_merge"),
    ("应拆分", "should_split"),
    ("不是真需求", "not_a_real_demand"),
]

MERGE_REVIEW_ACTIONS = [
    ("确认合并", "confirm_merge"),
    ("不合并", "reject_merge"),
    ("暂时不确定", "maybe_merge"),
    ("理由不对", "wrong_reason"),
    ("标题不好", "bad_title"),
    ("需要拆分", "needs_split"),
    ("重复建议", "duplicate_candidate"),
    ("不是同一需求", "not_same_demand"),
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

CLUSTER_REVIEW_LABELS = {
    "All": "全部",
    "good_cluster": "通过",
    "too_broad": "过宽",
    "too_narrow": "过窄",
    "wrong_grouping": "分组错误",
    "duplicate_cluster": "重复主题",
    "bad_title": "标题问题",
    "should_merge": "应合并",
    "should_split": "应拆分",
    "not_a_real_demand": "不是真需求",
}

MERGE_REVIEW_LABELS = {
    "All": "全部",
    "confirm_merge": "确认合并",
    "reject_merge": "不合并",
    "maybe_merge": "暂时不确定",
    "wrong_reason": "理由不对",
    "bad_title": "标题不好",
    "needs_split": "需要拆分",
    "duplicate_candidate": "重复建议",
    "not_same_demand": "不是同一需求",
}

PERSONA_LABELS = {
    "All": "全部",
    "investor": "投资人",
    "researcher": "研究员",
    "founder": "创始人",
    "content_team": "内容团队",
    "developer": "开发者",
    "operator": "运营",
    "strategy_bd": "战略与商务拓展",
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
    "ai_investment_research": "人工智能投资研究",
    "ai_hardtech": "人工智能硬科技",
    "content_production": "内容生产",
    "enterprise_knowledge_workflow": "企业知识工作流",
    "ai_agent_workflow": "人工智能智能体工作流",
    "developer_workflow": "开发者工具链",
    "general_workflow": "相关工作流",
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
        "标准化信号、已抽取痛点或需求主题候选。"
    )

    pain_tab, cluster_tab, merge_tab = st.tabs(["痛点校准", "需求主题审核", "合并建议审核"])
    with pain_tab:
        _render_pain_review_page()
    with cluster_tab:
        _render_cluster_review_page()
    with merge_tab:
        _render_merge_review_page()


def _render_pain_review_page() -> None:
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


def _render_cluster_review_page() -> None:
    items = load_cluster_review_items()
    summary = get_cluster_review_summary(items)
    _render_cluster_summary(summary)

    if st.button("重建需求主题报告", type="primary", key="rebuild_cluster_report"):
        rebuilt = build_cluster_report()
        st.success(
            "需求主题报告已重建："
            f"主题 {rebuilt.demand_clusters} 个，已审核主题 {rebuilt.reviewed_clusters} 个。"
        )

    if not items:
        st.info("还没有需求主题候选。请先运行 `demand-radar run-stage2` 或 `demand-radar run-cluster`。")
        return

    st.caption(f"当前显示 {len(items)} 个需求主题候选。")
    for item in items:
        _render_cluster_item(item)


def _render_merge_review_page() -> None:
    items = load_merge_review_items()
    summary = get_merge_review_summary(items)
    _render_merge_summary(summary)

    col_a, col_b = st.columns(2)
    if col_a.button("重建合并建议报告", type="primary", key="rebuild_merge_report"):
        rebuilt = build_merge_report()
        st.success(
            "合并建议报告已重建："
            f"候选 {rebuilt.merge_candidates} 个，已审核 {rebuilt.reviewed_candidates} 个。"
        )
    if col_b.button("重建已确认需求组", type="primary", key="rebuild_reviewed_groups"):
        groups = build_reviewed_cluster_groups()
        rebuilt = build_reviewed_groups_report()
        st.success(
            "已确认需求组已重建："
            f"生成 {len(groups)} 个需求组，覆盖 {rebuilt.included_clusters} 个主题。"
        )

    if not items:
        st.info("还没有合并建议。请先运行 `demand-radar run-stage25` 或 `demand-radar suggest-merges`。")
        return

    st.caption(f"当前显示 {len(items)} 条合并建议。")
    for item in items:
        _render_merge_item(item)


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


def _render_cluster_summary(summary: object) -> None:
    labels = summary.labels
    metric_values = [
        ("需求主题", summary.demand_clusters),
        ("单证据主题", summary.singleton_clusters),
        ("已审核主题", summary.reviewed_clusters),
        ("未审核主题", summary.unreviewed_clusters),
        ("审核记录", summary.cluster_reviews),
        ("通过", labels.get("good_cluster", 0)),
        ("过宽", labels.get("too_broad", 0)),
        ("过窄", labels.get("too_narrow", 0)),
        ("分组错误", labels.get("wrong_grouping", 0)),
        ("重复主题", labels.get("duplicate_cluster", 0)),
        ("标题问题", labels.get("bad_title", 0)),
        ("应合并", labels.get("should_merge", 0)),
        ("应拆分", labels.get("should_split", 0)),
        ("不是真需求", labels.get("not_a_real_demand", 0)),
    ]
    columns = st.columns(7)
    for index, (label, value) in enumerate(metric_values):
        columns[index % len(columns)].metric(label, value)


def _render_merge_summary(summary: object) -> None:
    metric_values = [
        ("需求主题", summary.demand_clusters),
        ("合并建议", summary.merge_candidates),
        ("强建议", summary.strong_candidates),
        ("中建议", summary.medium_candidates),
        ("已审核建议", summary.reviewed_candidates),
        ("确认合并", summary.confirmed_merges),
        ("拒绝合并", summary.rejected_merges),
        ("暂不确定", summary.maybe_merges),
        ("已确认需求组", summary.reviewed_groups),
    ]
    columns = st.columns(6)
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
    view = build_chinese_review_view(item)
    title = f"{view.title} - {_item_type_label(item.item_type)}"
    with st.expander(title, expanded=not item.reviewed):
        _render_metadata(item)
        left, right = st.columns([3, 2])
        with left:
            st.subheader("需求说明")
            st.markdown(f"**一句话总结：** {view.summary}")
            st.markdown(f"**证据说明：** {view.evidence_summary or '暂无明确证据说明'}")
            st.caption("页面只展示中文需求说明；如需核对英文原文，请打开来源链接。")
        with right:
            st.subheader("抽取结果")
            _render_extraction_fields(item, view)
            _render_review_status(item)
            _render_quarantine(item)
        _render_review_controls(item)


def _render_cluster_item(item: ClusterReviewItem) -> None:
    title = f"{item.cluster_title_zh} - 证据 {item.evidence_count} 条"
    with st.expander(title, expanded=not item.reviewed):
        left, right = st.columns([3, 2])
        with left:
            st.subheader("需求主题")
            st.markdown(f"**中文主题：** {item.cluster_title_zh}")
            st.markdown(f"**需求摘要：** {item.cluster_summary_zh}")
            st.markdown(f"**目标用户：** {_persona_list_label(item.personas)}")
            st.markdown(f"**相关领域：** {_domain_tags_label(item.domain_tags)}")
            st.markdown(f"**证据数量：** {item.evidence_count}")
            st.markdown(f"**来源数量：** {item.source_count}")
            st.markdown(f"**聚类置信度：** {item.cluster_confidence:.2f}")
            st.caption("这里展示的是中文需求主题候选；原始材料和痛点证据仍保留在本地 JSONL 状态文件中。")
        with right:
            st.subheader("审核状态")
            _render_cluster_review_status(item)
            st.markdown(f"**聚类方法：** {_cluster_method_label(item.cluster_method)}")
            st.markdown(f"**相关痛点：** {len(item.related_pain_point_ids)} 条")

        _render_cluster_lists(item)
        _render_cluster_review_controls(item)


def _render_merge_item(item: MergeReviewItem) -> None:
    title = (
        f"{_strength_label(item.strength)}建议 · 相似度 {item.similarity_score:.1f} · "
        f"{item.title_a} ↔ {item.title_b}"
    )
    with st.expander(title, expanded=not item.reviewed):
        left, right = st.columns([3, 2])
        with left:
            st.subheader("合并建议")
            st.markdown(f"**Cluster A：** {item.title_a}")
            st.markdown(f"**Cluster B：** {item.title_b}")
            st.markdown(f"**建议理由：** {item.merge_reason_zh}")
            if item.risk_note_zh:
                st.warning(item.risk_note_zh)
            st.caption("合并建议只是候选状态。只有人工确认后，才会生成已确认需求组。")
        with right:
            st.subheader("审核状态")
            _render_merge_review_status(item)
            st.markdown(f"**相似度：** {item.similarity_score:.1f}")
            st.markdown(f"**建议强度：** {_strength_label(item.strength)}")
            st.markdown(f"**共享用户：** {_persona_list_label(item.shared_personas)}")
            st.markdown(f"**共享领域：** {_domain_tags_label(item.shared_domain_tags)}")

        _render_merge_diagnostics(item)
        _render_merge_review_controls(item)


def _render_merge_diagnostics(item: MergeReviewItem) -> None:
    st.markdown("**共享关键词**")
    if item.shared_keywords:
        st.write("、".join(item.shared_keywords))
    else:
        st.caption("暂无")

    st.markdown("**字段相似度诊断**")
    score_columns = st.columns(3)
    scores = [
        ("标题", item.field_scores.get("title_similarity", 0)),
        ("摘要", item.field_scores.get("summary_similarity", 0)),
        ("痛点", item.field_scores.get("pain_description_similarity", 0)),
        ("替代方案", item.field_scores.get("workaround_similarity", 0)),
        ("用户角色", item.field_scores.get("persona_similarity", 0)),
        ("领域", item.field_scores.get("domain_similarity", 0)),
    ]
    for index, (label, score) in enumerate(scores):
        score_columns[index % len(score_columns)].metric(label, f"{score:.1f}")

    left, right = st.columns(2)
    with left:
        st.markdown("**Cluster A 代表性证据说明**")
        _render_list_or_empty(item.representative_quotes_a)
    with right:
        st.markdown("**Cluster B 代表性证据说明**")
        _render_list_or_empty(item.representative_quotes_b)


def _render_cluster_lists(item: ClusterReviewItem) -> None:
    st.markdown("**代表性痛点**")
    _render_list_or_empty(item.representative_pain_descriptions)
    st.markdown("**代表性证据说明**")
    _render_list_or_empty(item.representative_quotes)
    st.markdown("**当前替代方案**")
    _render_list_or_empty(item.current_workarounds)
    with st.expander("查看相关痛点编号"):
        st.write("，".join(item.related_pain_point_ids))


def _render_list_or_empty(values: list[str]) -> None:
    cleaned = [value for value in values if value]
    if not cleaned:
        st.caption("暂无")
        return
    for value in cleaned:
        st.markdown(f"- {value}")


def _render_cluster_review_status(item: ClusterReviewItem) -> None:
    if item.reviewed:
        st.success(f"已审核：{_cluster_review_label(item.latest_review_label or '')}")
        if item.latest_review_note:
            st.caption(_review_note_label(item.latest_review_note))
    else:
        st.warning("未审核")


def _render_merge_review_status(item: MergeReviewItem) -> None:
    if item.reviewed:
        st.success(f"已审核：{_merge_review_label(item.latest_review_label or '')}")
        if item.latest_review_note:
            st.caption(_review_note_label(item.latest_review_note))
    else:
        st.warning("未审核")


def _render_cluster_review_controls(item: ClusterReviewItem) -> None:
    key_base = item.cluster_id
    with st.form(f"cluster_review_form_{key_base}", clear_on_submit=False):
        note = st.text_area("审核备注", key=f"cluster_note_{key_base}")
        col_a, col_b, col_c = st.columns(3)
        expected_title = col_a.text_input("期望中文标题", key=f"cluster_title_{key_base}")
        should_merge_with = col_b.text_input("建议合并到主题编号", key=f"cluster_merge_{key_base}")
        should_split = col_c.checkbox("建议拆分", key=f"cluster_split_{key_base}")
        st.markdown("**审核动作**")
        button_columns = st.columns(5)
        submitted_label = None
        for index, (text, label) in enumerate(CLUSTER_REVIEW_ACTIONS):
            if button_columns[index % len(button_columns)].form_submit_button(text):
                submitted_label = label
        if submitted_label:
            add_cluster_review(
                item,
                label=submitted_label,
                reviewer_note=note.strip() or f"标记为{_cluster_review_label(submitted_label)}",
                expected_title_zh=expected_title.strip() or None,
                should_merge_with=should_merge_with.strip() or None,
                should_split=True if submitted_label == "should_split" or should_split else None,
            )
            st.success(f"已保存需求主题审核：{_cluster_review_label(submitted_label)}")
            st.rerun()


def _render_merge_review_controls(item: MergeReviewItem) -> None:
    key_base = item.merge_candidate_id
    with st.form(f"merge_review_form_{key_base}", clear_on_submit=False):
        note = st.text_area("审核备注", key=f"merge_note_{key_base}")
        col_a, col_b = st.columns(2)
        expected_title = col_a.text_input("期望合并后标题", key=f"merge_title_{key_base}")
        expected_summary = col_b.text_input("期望合并后摘要", key=f"merge_summary_{key_base}")
        st.markdown("**审核动作**")
        button_columns = st.columns(4)
        submitted_label = None
        for index, (text, label) in enumerate(MERGE_REVIEW_ACTIONS):
            if button_columns[index % len(button_columns)].form_submit_button(text):
                submitted_label = label
        if submitted_label:
            add_merge_review(
                item,
                label=submitted_label,
                reviewer_note=note.strip() or f"标记为{_merge_review_label(submitted_label)}",
                expected_group_title_zh=expected_title.strip() or None,
                expected_group_summary_zh=expected_summary.strip() or None,
            )
            st.success(f"已保存合并建议审核：{_merge_review_label(submitted_label)}")
            st.rerun()


def _render_metadata(item: ReviewItem) -> None:
    metadata = [
        f"来源：`{_source_name_label(item.source_name or '')}` / `{_source_type_label(item.source_type or '')}`",
        f"语言：`{_language_label(item.language or '')}`",
        f"领域标签：`{_domain_tags_label(item.domain_tags)}`",
    ]
    st.markdown("  \n".join(metadata))
    if item.url:
        st.markdown(f"原文追溯：[打开来源链接]({item.url})")
    st.caption("内部编号已隐藏；需要审计时可查看本地数据文件。")


def _render_extraction_fields(item: ReviewItem, view: object) -> None:
    rows = [
        ("用户角色", _persona_label(item.persona or "")),
        ("场景", view.scenario),
        ("待完成任务", view.job_to_be_done),
        ("痛点", view.pain_description),
        ("当前替代方案", view.current_workaround),
        ("频率信号", view.frequency_signal),
        ("付费信号", view.payment_signal),
        ("置信度", f"{item.confidence:.2f}" if item.confidence is not None else None),
    ]
    for label, value in rows:
        st.markdown(f"**{label}:** {value or ''}")


def _render_review_status(item: ReviewItem) -> None:
    if item.reviewed:
        st.success(f"已审核：{_review_label(item.latest_review_label or '')}")
        if item.latest_review_note:
            st.caption(_review_note_label(item.latest_review_note))
    else:
        st.warning("未审核")


def _render_quarantine(item: ReviewItem) -> None:
    if item.item_type != "quarantine":
        return
    st.error(f"隔离原因：{_quarantine_reason_label(item.quarantine_reason or '')}")
    st.caption("隔离原始载荷已在页面隐藏，避免英文原文干扰判断；需要审计时可查看本地数据文件。")


def _render_review_controls(item: ReviewItem) -> None:
    key_base = _item_key(item)
    with st.form(f"review_form_{key_base}", clear_on_submit=False):
        note = st.text_area("审核备注", key=f"note_{key_base}")
        col_a, col_b, col_c = st.columns(3)
        expected_persona = col_a.text_input("期望用户角色", key=f"persona_{key_base}")
        expected_quote = col_b.text_input("期望证据说明", key=f"quote_{key_base}")
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


def _item_key(item: ReviewItem) -> str:
    return item.pain_point_id or item.normalized_signal_id or item.raw_signal_id


def _unique_values(values: Iterable[str | None]) -> list[str]:
    return sorted({value for value in values if value})


def _range_label(value: str) -> str:
    return RANGE_LABELS.get(value, value)


def _review_label(value: str) -> str:
    return REVIEW_LABELS.get(value, value)


def _cluster_review_label(value: str) -> str:
    return CLUSTER_REVIEW_LABELS.get(value, value)


def _merge_review_label(value: str) -> str:
    return MERGE_REVIEW_LABELS.get(value, value)


def _strength_label(value: str) -> str:
    labels = {
        "strong": "强",
        "medium": "中",
        "weak": "弱",
    }
    return labels.get(value, value or "未知")


def _persona_label(value: str) -> str:
    return PERSONA_LABELS.get(value, value or "未知")


def _persona_list_label(values: list[str]) -> str:
    if not values:
        return "未标注"
    return "，".join(_persona_label(value) for value in values)


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


def _cluster_method_label(value: str) -> str:
    labels = {
        "rule_similarity_v1": "轻量规则相似度",
    }
    return labels.get(value, value or "未知")


def _quarantine_reason_label(value: str) -> str:
    return QUARANTINE_REASON_LABELS.get(value, value or "未知")


def _review_note_label(value: str) -> str:
    known_notes = {
        "UI validation: quote is too narrow": "界面验证：证据引用范围过窄。",
        "UI validation: should be quarantined": "界面验证：这条应进入隔离区。",
        "Looks right.": "人工判断：抽取结果基本正确。",
        "Quote is useful but thin.": "人工判断：证据可用，但信息偏薄。",
        "Latest review should win.": "人工判断：以最新审核为准。",
    }
    if value in known_notes:
        return known_notes[value]
    if looks_like_english(value):
        return "已有英文审核备注已隐藏；需要审计时可查看本地校准审核记录文件。"
    return value


if __name__ == "__main__":
    main()
