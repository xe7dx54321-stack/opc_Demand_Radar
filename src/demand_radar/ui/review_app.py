"""Streamlit app for local calibration review."""



from __future__ import annotations



from typing import Iterable



import streamlit as st



from demand_radar.batch.batch_report import build_batch_summary_report

from demand_radar.batch.batch_summary import build_batch_summary

from demand_radar.calibration.calibration_schema import VALID_REVIEW_LABELS

from demand_radar.clustering.cluster_report import build_cluster_report

from demand_radar.clustering.merge_report import build_merge_report, build_reviewed_groups_report

from demand_radar.clustering.merge_store import build_reviewed_cluster_groups

from demand_radar.reporting.calibration_report import build_calibration_report

from demand_radar.semantic_merge.semantic_merge_schema import (

    VALID_SEMANTIC_HUMAN_AUDIT_LABELS,

)

from demand_radar.semantic_merge.semantic_merge_store import (

    append_semantic_merge_human_audit,

    load_ai_reviewed_cluster_groups,

    load_human_exception_items,

    load_semantic_merge_judgments,

)



from demand_radar.ui.evidence_gap_service import get_gap_analyses, get_collection_plans
from demand_radar.ui.targeted_expansion_service import get_expansion_summary, get_targeted_validations, get_truth_score_deltas
from demand_radar.ui.lineage_service import get_candidate_lineages, get_targeted_evidence_attributions, get_stable_truth_score_deltas
from demand_radar.ui.truth_review_service import get_truth_scores, submit_truth_review
from demand_radar.ui.cluster_review_service import (

    ClusterReviewItem,

    add_cluster_review,

    filter_cluster_items_by_batch,

    get_available_cluster_batches,

    get_cluster_review_summary,

    load_cluster_review_items,

)

from demand_radar.ui.chinese_presenter import build_chinese_review_view, looks_like_english

from demand_radar.ui.merge_review_service import (

    MergeReviewItem,

    add_merge_review,

    filter_merge_items_by_batch,

    get_available_merge_batches,

    get_merge_review_summary,

    load_merge_review_items,

)

from demand_radar.ui.review_service import (

    ReviewItem,

    add_review,

    filter_items_by_batch,

    get_available_batches,

    get_review_summary,

    load_review_items,

)



from demand_radar.semantic_merge.llm_comparison_report import (

    build_semantic_merge_comparison_report,

    ComparisonSummary,

)

from demand_radar.semantic_merge.semantic_merge_store import (

    load_ai_reviewed_cluster_groups as _load_ai_groups,

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



BATCH_LABELS = {

    "All": "全部批次",

    "default": "默认批次",

    "batch_stage26_ai_research": "人工智能投资/产业研究批次",

    "batch_stage26_content_workflow": "内容选题与生产批次",

    "batch_stage26_agent_workflow": "智能体工作流批次",

    "batch_stage26_devtools": "开发者工具链批次",

    "batch_stage26_enterprise_knowledge": "企业知识工作流批次",

    "batch_stage26_noise": "噪音与弱信号批次",

}



SIGNAL_FOCUS_LABELS = {

    "pain": "痛点",

    "workaround": "替代方案",

    "competitor_gap": "竞品缺口",

    "feature_gap": "功能缺口",

    "weak_signal": "弱信号",

    "noise": "噪音",

    "hiring_signal": "招聘信号",

    "workflow_repetition": "重复工作流",

}



EXPECTED_QUALITY_LABELS = {

    "strong": "强",

    "medium": "中",

    "weak": "弱",

    "noise": "噪音",

}





def main() -> None:

    st.set_page_config(page_title="需求雷达审核台", layout="wide")

    _hide_streamlit_chrome()

    st.title("需求雷达审核台")

    st.caption(

        "本地校准审核界面。审核结果会作为反馈记忆追加保存，不会修改原始信号、"

        "标准化信号、已抽取痛点或需求主题候选。"

    )



    pain_items = load_review_items()

    cluster_items = load_cluster_review_items()

    merge_items = load_merge_review_items()

    batch_filter = _sidebar_batch_filter(pain_items, cluster_items, merge_items)

    _render_current_batch_summary(batch_filter)



    pain_tab, cluster_tab, merge_tab, ai_judge_tab, exception_tab, llm_tab, truth_tab, gap_tab, expansion_tab, lineage_tab, stage35_tab, real_evidence_tab, acquisition_tab, mvp_b_tab, batch_tab = st.tabs(
        ["痛点校准", "需求主题候选", "合并建议审核", "AI合并判断", "人工异常队列", "LLM合并对比", "真实需求评分", "证据缺口分析", "定向证据扩展", "候选谱系追踪",
        "Stage 3.5 定向验证", "真实证据校准", "自动采集", "MVP-B 痛点抽取", "批次总览"]
    )

    with pain_tab:

        _render_pain_review_page(pain_items, batch_filter)

    with cluster_tab:

        _render_cluster_review_page(cluster_items, batch_filter)

    with merge_tab:

        _render_merge_review_page(merge_items, batch_filter)

    with ai_judge_tab:

        _render_ai_judge_page(batch_filter)

    with exception_tab:

        _render_exception_queue_page(batch_filter)

    with llm_tab:

        _render_llm_comparison_page()


    with truth_tab:
        _render_truth_scoring_page()

    with gap_tab:
        _render_evidence_gap_page()

    with expansion_tab:
        _render_targeted_expansion_page()

    with lineage_tab:
        _render_lineage_page()

    with stage35_tab:
        _render_stage35_page()


    with real_evidence_tab:
        _render_real_evidence_page()


    with real_evidence_tab:
        _render_real_evidence_page()


    with acquisition_tab:
        _render_acquisition_page()


    with mvp_b_tab:
        _render_mvp_b_page()

    with batch_tab:

        _render_batch_overview_page(batch_filter)





def _render_pain_review_page(items: list[ReviewItem], batch_filter: str) -> None:

    items = filter_items_by_batch(items, batch_filter)

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





def _render_cluster_review_page(items: list[ClusterReviewItem], batch_filter: str) -> None:

    items = filter_cluster_items_by_batch(items, batch_filter)

    summary = get_cluster_review_summary(items)

    _render_cluster_summary(summary)



    if st.button("重建需求主题报告", type="primary", key="rebuild_cluster_report"):

        rebuilt = build_cluster_report()

        st.success(

            "需求主题报告已重建："

            f"主题 {rebuilt.demand_clusters} 个，已审核主题 {rebuilt.reviewed_clusters} 个。"

        )



    if not items:

        st.info("还没有需求主题候选。请先运行需求主题生成流程。")

        return



    st.caption(f"当前显示 {len(items)} 个需求主题候选。")

    for item in items:

        _render_cluster_item(item)





def _render_merge_review_page(items: list[MergeReviewItem], batch_filter: str) -> None:

    items = filter_merge_items_by_batch(items, batch_filter)

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

        st.info("还没有合并建议。请先运行合并建议生成流程。")

        return



    st.caption(f"当前显示 {len(items)} 条合并建议。")

    for item in items:

        _render_merge_item(item)





def _render_batch_overview_page(batch_filter: str) -> None:

    result = build_batch_summary()

    if st.button("重建批次总览报告", type="primary", key="rebuild_batch_report"):

        rebuilt = build_batch_summary_report()

        st.success(

            "批次总览报告已重建："

            f"批次数 {len(rebuilt.batches)}，第三阶段准备度："

            f"{_readiness_label(rebuilt.readiness.ready_for_truth_scoring)}。"

        )

        result = rebuilt



    selected_batches = result.batches if batch_filter == "All" else [

        batch for batch in result.batches if batch.batch_id == batch_filter

    ]

    st.subheader("批次质量矩阵")

    st.caption("批次只是分析维度，不会修改原始信号、痛点、需求主题或合并建议。")

    if not selected_batches:

        st.info("当前批次没有可展示的数据。")

        return



    for batch in selected_batches:

        with st.expander(_batch_label(batch.batch_id), expanded=True):

            cols = st.columns(6)

            cols[0].metric("原始信号", batch.raw_signals)

            cols[1].metric("痛点", batch.pain_points)

            cols[2].metric("隔离率", _percent(batch.quarantine_rate))

            cols[3].metric("需求主题", batch.demand_clusters)

            cols[4].metric("合并建议", batch.merge_candidates)

            cols[5].metric("已确认需求组", batch.reviewed_groups)

            st.markdown(

                f"抽取产出率：`{_percent(batch.extraction_yield)}` · "

                f"单证据主题比例：`{_percent(batch.singleton_rate)}` · "

                f"合并建议密度：`{_percent(batch.merge_candidate_rate)}`"

            )

            st.markdown(

                f"校准审核：通过 `{batch.good_extractions}`，较弱 `{batch.weak_extractions}`，"

                f"误报 `{batch.false_positives}`，引用问题 `{batch.bad_quotes}`，应隔离 `{batch.should_quarantine}`。"

            )



    st.subheader("第三阶段准备度")

    readiness = result.readiness

    readiness_cols = st.columns(4)

    readiness_cols[0].metric("样本量达标", "是" if readiness.sample_size_ok else "否")

    readiness_cols[1].metric("痛点量达标", "是" if readiness.pain_volume_ok else "否")

    readiness_cols[2].metric("需求组达标", "是" if readiness.group_volume_ok else "否")

    readiness_cols[3].metric("收敛达标", "是" if readiness.clustering_convergence_ok else "否")

    st.info(

        f"真值评分准备度：{_readiness_label(readiness.ready_for_truth_scoring)}。"

        f"{readiness.recommendation}"

    )





def _sidebar_batch_filter(

    pain_items: list[ReviewItem],

    cluster_items: list[ClusterReviewItem],

    merge_items: list[MergeReviewItem],

) -> str:

    batches = sorted(

        {

            *get_available_batches(pain_items),

            *get_available_cluster_batches(cluster_items),

            *get_available_merge_batches(merge_items),

        }

    )

    with st.sidebar:

        st.header("全局批次")

        return st.selectbox("批次筛选", ["All", *batches], format_func=_batch_label)





def _render_current_batch_summary(batch_filter: str) -> None:

    result = build_batch_summary()

    batch = result.overall if batch_filter == "All" else next(

        (item for item in result.batches if item.batch_id == batch_filter),

        None,

    )

    st.caption(f"当前批次：{_batch_label(batch_filter)}")

    if batch is None:

        return

    columns = st.columns(5)

    columns[0].metric("原始信号", batch.raw_signals)

    columns[1].metric("痛点", batch.pain_points)

    columns[2].metric("需求主题", batch.demand_clusters)

    columns[3].metric("合并建议", batch.merge_candidates)

    columns[4].metric("已确认需求组", batch.reviewed_groups)





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

            st.markdown(f"**批次：** {_batch_list_label(item.batch_ids)}")

            st.markdown(f"**信号关注点：** {_signal_focus_list_label(item.signal_focuses)}")

            st.markdown(f"**预期质量：** {_quality_mix_label(item.expected_quality_mix)}")

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

            st.markdown(f"**主题甲：** {item.title_a}")

            st.markdown(f"**主题乙：** {item.title_b}")

            st.markdown(f"**建议理由：** {item.merge_reason_zh}")

            if item.risk_note_zh:

                st.warning(item.risk_note_zh)

            st.caption("合并建议只是候选状态。只有人工确认后，才会生成已确认需求组。")

        with right:

            st.subheader("审核状态")

            _render_merge_review_status(item)

            st.markdown(f"**批次：** {_batch_list_label(item.batch_ids)}")

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

        st.markdown("**主题甲代表性证据说明**")

        _render_list_or_empty(item.representative_quotes_a)

    with right:

        st.markdown("**主题乙代表性证据说明**")

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

        f"批次：`{_batch_label(item.batch_id or 'default')}`",

        f"信号关注点：`{_signal_focus_label(item.signal_focus or '')}`",

        f"预期质量：`{_expected_quality_label(item.expected_quality or '')}`",

        f"来源：`{_source_name_label(item.source_name or '')}` / `{_source_type_label(item.source_type or '')}`",

        f"语言：`{_language_label(item.language or '')}`",

        f"领域标签：`{_domain_tags_label(item.domain_tags)}`",

    ]

    st.markdown("  \n".join(metadata))

    if item.url:

        st.markdown(f"原文追溯：[打开来源链接]({item.url})")

    if item.source_note:

        st.caption(f"来源备注：{item.source_note}")

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





def _hide_streamlit_chrome() -> None:

    st.markdown(

        """

        <style>

        [data-testid="stDeployButton"],

        [data-testid="stToolbar"],

        #MainMenu,

        footer {

            display: none !important;

            visibility: hidden !important;

        }

        header {

            visibility: hidden !important;

        }

        </style>

        """,

        unsafe_allow_html=True,

    )





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





def _batch_label(value: str) -> str:

    return BATCH_LABELS.get(value, value or "默认批次")





def _percent(value: float | None) -> str:

    if value is None:

        return "暂无"

    return f"{value * 100:.1f}%"





def _readiness_label(value: str) -> str:

    labels = {

        "yes": "已具备",

        "partial": "部分具备",

        "no": "暂不具备",

    }

    return labels.get(value, value or "未知")





def _batch_list_label(values: list[str]) -> str:

    cleaned = [value for value in values if value]

    if not cleaned:

        return _batch_label("default")

    return "，".join(_batch_label(value) for value in cleaned)





def _signal_focus_label(value: str) -> str:

    return SIGNAL_FOCUS_LABELS.get(value, value or "未标注")





def _signal_focus_list_label(values: list[str]) -> str:

    cleaned = [value for value in values if value]

    if not cleaned:

        return "未标注"

    return "，".join(_signal_focus_label(value) for value in cleaned)





def _expected_quality_label(value: str) -> str:

    return EXPECTED_QUALITY_LABELS.get(value, value or "未标注")





def _quality_mix_label(values: dict[str, int]) -> str:

    if not values:

        return "未标注"

    return "，".join(

        f"{_expected_quality_label(key)} {value}"

        for key, value in sorted(values.items())

    )





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





# ---------------------------------------------------------------------------

# AI 合并判断 Tab

# ---------------------------------------------------------------------------



_JUDGMENT_ACTION_LABELS = {

    "auto_confirm": "自动确认合并",

    "auto_reject": "自动拒绝合并",

    "human_exception": "进入人工异常队列",

}





def _render_ai_judge_page(batch_filter: str) -> None:

    """Render the AI semantic merge judgment tab."""

    st.subheader("AI 合并判断")

    st.caption(

        "AI 已自动处理高置信合并与拒绝。此页面用于查看 AI 判断结果和分布，"

        "不需要逐条审核。如需处理异常项，请切换到「人工异常队列」Tab。"

    )



    # Judge source selector (Stage 2.9C)

    _ai_src_options = ["rule_based", "llm", "calibrated_llm"]

    _ai_src_labels = {

        "rule_based": "规则判断 (rule_based_stub)",

        "llm": "真实 LLM 判断 (2.9B)",

        "calibrated_llm": "校准 LLM 判断 (2.9C)",

    }

    judge_source = st.radio(

        "判断来源 (Judge Source)",

        _ai_src_options,

        index=0,

        format_func=lambda x: _ai_src_labels.get(x, x),

        horizontal=True,

        key="ai_judge_source",

    )

    _ai_judgment_paths = {

        "rule_based": "data/processed/semantic_merge_judgments.jsonl",

        "llm": "data/processed/llm_semantic_merge_judgments.jsonl",

        "calibrated_llm": "data/processed/calibrated_llm_semantic_merge_judgments.jsonl",

    }

    judgments = load_semantic_merge_judgments(_ai_judgment_paths[judge_source])

    if not judgments:

        st.info(f"暂无 {_ai_src_labels[judge_source]} 记录。请先运行对应 stage 命令。")

        return



    if batch_filter != "All":

        pass  # judgments don't carry batch_id; show all



    auto_confirm_count = sum(1 for j in judgments if j.auto_action == "auto_confirm")

    auto_reject_count = sum(1 for j in judgments if j.auto_action == "auto_reject")

    exception_count = sum(1 for j in judgments if j.auto_action == "human_exception")



    cols = st.columns(4)

    cols[0].metric("总判断数", len(judgments))

    cols[1].metric("自动确认", auto_confirm_count)

    cols[2].metric("自动拒绝", auto_reject_count)

    cols[3].metric("进入异常队列", exception_count)



    exception_rate = exception_count / len(judgments) if judgments else None

    if exception_rate is not None:

        rate_pct = f"{exception_rate * 100:.1f}%"

        color = "normal" if exception_rate <= 0.45 else "inverse"

        st.metric("人工异常率", rate_pct, delta=None, delta_color=color)



    st.divider()



    action_filter = st.selectbox(

        "筛选动作类型",

        ["全部", "auto_confirm", "auto_reject", "human_exception"],

        format_func=lambda x: "全部" if x == "全部" else _JUDGMENT_ACTION_LABELS.get(x, x),

    )



    filtered = judgments if action_filter == "全部" else [j for j in judgments if j.auto_action == action_filter]

    st.caption(f"当前显示 {len(filtered)} 条，共 {len(judgments)} 条判断")



    for idx, judgment in enumerate(filtered, start=1):

        action_label = _JUDGMENT_ACTION_LABELS.get(judgment.auto_action, judgment.auto_action)

        with st.expander(

            f"#{idx} [{action_label}] {judgment.cluster_id_a} ↔ {judgment.cluster_id_b} "

            f"（置信度 {judgment.confidence:.2f}）",

            expanded=False,

        ):

            col1, col2 = st.columns(2)

            col1.caption("判断结果")

            col1.write(f"**决策**: {judgment.decision}")

            col1.write(f"**自动动作**: {action_label}")

            col1.write(f"**置信度**: {judgment.confidence:.2f}")

            col1.write(f"**判断模式**: {judgment.judge_mode}")

            col2.caption("冲突标记")

            if judgment.conflict_flags:

                for flag in judgment.conflict_flags:

                    col2.write(f"⚠️ {flag}")

            else:

                col2.write("无冲突标记")



            st.caption("AI 判断理由")

            st.write(judgment.reason_zh)

            if judgment.evidence_alignment_zh:

                st.caption("证据对齐说明")

                st.write(judgment.evidence_alignment_zh)

            if judgment.workflow_judgment_zh:

                st.caption("工作流判断")

                st.write(judgment.workflow_judgment_zh)

            if judgment.suggested_group_title_zh:

                st.success(f"建议合并后标题：{judgment.suggested_group_title_zh}")

            if judgment.suggested_group_summary_zh:

                st.caption("建议合并后摘要")

                st.write(judgment.suggested_group_summary_zh)





# ---------------------------------------------------------------------------

# 人工异常队列 Tab

# ---------------------------------------------------------------------------



_EXCEPTION_AUDIT_ACTIONS = [

    ("确认合并", "correct_to_confirm"),

    ("拒绝合并", "correct_to_reject"),

    ("AI 理由不好", "bad_reason"),

    ("暂不处理", "ai_correct"),

    ("需要重跑", "needs_rerun"),

]





def _render_exception_queue_page(batch_filter: str) -> None:

    """Render the human exception queue tab."""

    st.subheader("人工异常队列")

    st.caption(

        "以下是 AI 无法自动处理的合并判断项，需要人工协助裁决。"

        "AI 已自动处理高置信合并与拒绝；此处主要用于处理低置信、冲突或证据不足的情况。"

    )



    # Exception source selector (Stage 2.9C defaults to calibrated_llm)

    _exc_src_options = ["calibrated_llm", "llm", "rule_based"]

    _exc_src_labels = {

        "calibrated_llm": "校准 LLM 异常队列 (2.9C) [默认]",

        "llm": "真实 LLM 异常队列 (2.9B)",

        "rule_based": "规则判断异常队列 (rule_based)",

    }

    exc_source = st.radio(

        "异常来源 (Exception Source)",

        _exc_src_options,

        index=0,

        format_func=lambda x: _exc_src_labels.get(x, x),

        horizontal=True,

        key="exception_source",

    )

    _exc_paths = {

        "calibrated_llm": "data/processed/calibrated_llm_human_exception_queue.jsonl",

        "llm": "data/processed/llm_human_exception_queue.jsonl",

        "rule_based": "data/processed/human_exception_queue.jsonl",

    }

    exceptions = load_human_exception_items(_exc_paths[exc_source])

    if not exceptions:

        st.success(f"{_exc_src_labels[exc_source]} 队列为空。AI 已自动处理，或尚未运行对应 stage。")

        return



    high = [item for item in exceptions if item.priority == "high"]

    medium = [item for item in exceptions if item.priority == "medium"]

    low = [item for item in exceptions if item.priority == "low"]



    cols = st.columns(3)

    cols[0].metric("高优先级", len(high))

    cols[1].metric("中优先级", len(medium))

    cols[2].metric("低优先级", len(low))



    st.divider()



    priority_filter = st.selectbox(

        "按优先级筛选",

        ["全部", "high", "medium", "low"],

        format_func=lambda x: {"全部": "全部", "high": "高优先级", "medium": "中优先级", "low": "低优先级"}.get(x, x),

    )



    filtered = exceptions if priority_filter == "全部" else [item for item in exceptions if item.priority == priority_filter]

    st.caption(f"当前显示 {len(filtered)} 条，共 {len(exceptions)} 条异常")



    for idx, item in enumerate(filtered, start=1):

        priority_label = {"high": "🔴 高", "medium": "🟡 中", "low": "🟢 低"}.get(item.priority, item.priority)

        with st.expander(

            f"#{idx} [{priority_label}] {item.cluster_id_a} ↔ {item.cluster_id_b}",

            expanded=item.priority == "high",

        ):

            st.caption("异常原因")

            st.write(item.exception_reason)



            col1, col2 = st.columns(2)

            col1.write(f"**AI 原始决策**: {item.decision}")

            col1.write(f"**置信度**: {item.confidence:.2f}")

            if item.conflict_flags:

                col2.caption("冲突标记")

                for flag in item.conflict_flags:

                    col2.write(f"⚠️ {flag}")



            st.caption("AI 判断理由")

            st.write(item.reason_zh)



            st.caption("人工审核操作")

            note = st.text_input(

                "审核备注（可选）",

                key=f"exception_note_{item.exception_id}_{idx}",

                placeholder="输入备注...",

            )

            action_cols = st.columns(len(_EXCEPTION_AUDIT_ACTIONS))

            for col, (label, audit_label) in zip(action_cols, _EXCEPTION_AUDIT_ACTIONS):

                if col.button(label, key=f"exception_{audit_label}_{item.exception_id}_{idx}"):

                    corrected = None

                    if audit_label == "correct_to_confirm":

                        corrected = "confirm_merge"

                    elif audit_label == "correct_to_reject":

                        corrected = "reject_merge"

                    try:

                        append_semantic_merge_human_audit(

                            judgment_id=item.judgment_id,

                            merge_candidate_id=item.merge_candidate_id,

                            label=audit_label,

                            reviewer_note=note or None,

                            corrected_decision=corrected,

                        )

                        st.success(f"已记录审核操作：{label}")

                        st.rerun()

                    except Exception as exc:

                        st.error(f"保存审核记录失败：{exc}")





# ---------------------------------------------------------------------------

# LLM 合并对比 Tab

# ---------------------------------------------------------------------------



def _render_llm_comparison_page() -> None:

    """Render the LLM vs rule_based semantic merge comparison tab."""

    st.subheader("LLM 合并对比")

    st.caption(

        "对比 rule_based_stub 与真实 LLM 的语义合并判断结果。"

        "运行 demand-radar run-stage29 后此页面将显示对比数据。"

        "LLM 结果单独存储，不会覆盖 rule_based 结果。"

    )



    from pathlib import Path

    llm_path = Path("data/processed/llm_semantic_merge_judgments.jsonl")

    if not llm_path.exists() or not llm_path.read_text(encoding="utf-8").strip():

        st.info(

            "尚无 LLM 语义合并判断记录。"

            "请先配置 .env 并运行 demand-radar run-stage29，"

            "或运行 demand-radar run-stage29 --fake-llm 用测试模式体验流程。"

        )

        return



    # Judge source selector (Stage 2.9C adds calibrated_llm)

    _llm_src_options = ["rule_based", "llm", "calibrated_llm"]

    _llm_src_labels = {

        "rule_based": "规则判断 (rule_based_stub)",

        "llm": "真实 LLM 判断 (2.9B)",

        "calibrated_llm": "校准 LLM 判断 (2.9C)",

    }

    judge_source = st.radio(

        "判断来源",

        _llm_src_options,

        index=1,

        format_func=lambda x: _llm_src_labels.get(x, x),

        horizontal=True,

        key="llm_comparison_source",

    )



    from demand_radar.semantic_merge.semantic_merge_store import load_semantic_merge_judgments

    _cmp_judgment_paths = {

        "rule_based": "data/processed/semantic_merge_judgments.jsonl",

        "llm": "data/processed/llm_semantic_merge_judgments.jsonl",

        "calibrated_llm": "data/processed/calibrated_llm_semantic_merge_judgments.jsonl",

    }

    _cmp_group_paths = {

        "rule_based": "data/processed/ai_reviewed_cluster_groups.jsonl",

        "llm": "data/processed/llm_ai_reviewed_cluster_groups.jsonl",

        "calibrated_llm": "data/processed/calibrated_llm_ai_reviewed_cluster_groups.jsonl",

    }

    _cmp_exception_paths = {

        "rule_based": "data/processed/human_exception_queue.jsonl",

        "llm": "data/processed/llm_human_exception_queue.jsonl",

        "calibrated_llm": "data/processed/calibrated_llm_human_exception_queue.jsonl",

    }

    judgments = load_semantic_merge_judgments(_cmp_judgment_paths[judge_source])

    groups = _load_ai_groups(_cmp_group_paths[judge_source])

    exception_path = _cmp_exception_paths[judge_source]



    from demand_radar.semantic_merge.semantic_merge_store import load_human_exception_items

    exceptions = load_human_exception_items(exception_path)



    confirmed = sum(1 for j in judgments if j.auto_action == "auto_confirm")

    rejected = sum(1 for j in judgments if j.auto_action == "auto_reject")

    human_exc = sum(1 for j in judgments if j.auto_action == "human_exception")

    exc_rate = human_exc / len(judgments) if judgments else None



    cols = st.columns(5)

    cols[0].metric("总判断", len(judgments))

    cols[1].metric("自动确认", confirmed)

    cols[2].metric("自动拒绝", rejected)

    cols[3].metric("人工异常", human_exc)

    cols[4].metric("AI 需求组", len(groups))

    if exc_rate is not None:

        color = "normal" if exc_rate <= 0.45 else "inverse"

        st.metric("异常率", f"{exc_rate * 100:.1f}%", delta_color=color)



    # Comparison summary if both exist

    comparison_report = Path("outputs/llm_semantic_merge_comparison_report.md")

    if comparison_report.exists():

        st.divider()

        st.subheader("对比报告摘要")

        content = comparison_report.read_text(encoding="utf-8")

        lines_out = []

        for line in content.splitlines():

            if line.startswith("## Representative Examples"):

                break

            lines_out.append(line)

        st.markdown("\n".join(lines_out))



    st.divider()

    st.caption(f"当前显示 {len(judgments)} 条 {judge_source} 判断；AI 需求组 {len(groups)} 个")

    if st.button("重新生成对比报告", key="rebuild_comparison"):

        try:

            build_semantic_merge_comparison_report()

            st.success("对比报告已重新生成。")

            st.rerun()

        except Exception as exc:

            st.error(f"生成失败：{exc}")



def _render_truth_scoring_page() -> None:
    """Render the Stage 3 Truth Scoring review tab."""
    st.header("\u771f\u5b9e\u9700\u6c42\u8bc4\u5206 (Stage 3 Truth Scoring)")
    scores = get_truth_scores()
    if not scores:
        st.info("\u6682\u65e0\u8bc4\u5206\u7ed3\u679c\u3002\u8bf7\u5148\u8fd0\u884c: demand-radar run-stage3 --source calibrated_llm")
        return

    level_counts = {"strong": 0, "medium": 0, "weak": 0, "insufficient": 0}
    action_counts: dict[str, int] = {}
    for s in scores:
        level_counts[s.truth_level] = level_counts.get(s.truth_level, 0) + 1
        action_counts[s.recommended_next_action] = action_counts.get(s.recommended_next_action, 0) + 1

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("\U0001f7e2 Strong", level_counts.get("strong", 0))
    col2.metric("\U0001f7e1 Medium", level_counts.get("medium", 0))
    col3.metric("\U0001f7e0 Weak", level_counts.get("weak", 0))
    col4.metric("\U0001f534 Insufficient", level_counts.get("insufficient", 0))

    proceed = action_counts.get("proceed_to_fit_scoring", 0)
    needs_ev = action_counts.get("needs_more_evidence", 0)
    keep = action_counts.get("keep_watch", 0)
    discard = action_counts.get("discard", 0)
    st.caption(
        f"\u53ef\u8fdb Fit Scoring: **{proceed}** | "
        f"\u9700\u66f4\u591a\u8bc1\u636e: **{needs_ev}** | "
        f"\u89c2\u5bdf\u4e2d: **{keep}** | "
        f"\u5efa\u8bae\u4e22\u5f03: **{discard}**"
    )
    st.divider()

    LEVEL_EMOJI = {"strong": "\U0001f7e2", "medium": "\U0001f7e1", "weak": "\U0001f7e0", "insufficient": "\U0001f534"}
    ACTION_LABELS = {
        "proceed_to_fit_scoring": "\u53ef\u8fdb\u884c Fit Scoring",
        "needs_more_evidence": "\u9700\u8981\u66f4\u591a\u8bc1\u636e",
        "keep_watch": "\u6301\u7eed\u89c2\u5bdf",
        "discard": "\u5efa\u8bae\u4e22\u5f03",
    }

    sorted_scores = sorted(scores, key=lambda x: -x.truth_score)
    for s in sorted_scores:
        emoji = LEVEL_EMOJI.get(s.truth_level, "")
        with st.expander(f"{emoji} {s.group_title_zh} | {s.truth_score:.1f}\u5206 | {ACTION_LABELS.get(s.recommended_next_action, s.recommended_next_action)}"):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**Truth Score:** {s.truth_score:.1f} / 100")
                st.markdown(f"**Level:** {emoji} {s.truth_level}")
                st.markdown(f"**Next Action:** {ACTION_LABELS.get(s.recommended_next_action, s.recommended_next_action)}")
                st.markdown(f"**Evidence Count:** {s.evidence_count}")
                st.markdown(f"**Source Count:** {s.source_count}")
                if s.personas:
                    st.markdown(f"**Personas:** {', '.join(s.personas)}")
                if s.domain_tags:
                    st.markdown(f"**Domain Tags:** {', '.join(s.domain_tags)}")
            with c2:
                st.markdown("**Dimension Scores:**")
                dim_labels = {
                    "pain_evidence_strength": "\u75db\u70b9\u8bc1\u636e\u5f3a\u5ea6",
                    "frequency_repetition": "\u91cd\u590d\u9891\u7387",
                    "existing_workaround": "\u5df2\u6709\u66ff\u4ee3\u65b9\u6848",
                    "willingness_to_pay": "\u4ed8\u8d39\u610f\u613f\u4fe1\u53f7",
                    "persona_clarity": "\u7528\u6237\u753b\u50cf\u6e05\u6670\u5ea6",
                }
                for dim, label in dim_labels.items():
                    val = s.dimension_scores.get(dim, 0)
                    st.markdown(f"- {label}: **{val:.1f}**")

            if s.positive_signals:
                st.markdown("**\u6b63\u5411\u4fe1\u53f7:**")
                for sig in s.positive_signals:
                    st.markdown(f"  - {sig}")
            if s.negative_signals:
                st.markdown("**\u8d1f\u5411\u4fe1\u53f7:**")
                for sig in s.negative_signals:
                    st.markdown(f"  - {sig}")
            if s.risk_flags:
                st.markdown("**\u98ce\u9669\u6807\u8bc6:**")
                for flag in s.risk_flags:
                    st.markdown(f"  - `{flag}`")
            st.markdown(f"**\u8bc4\u5206\u7406\u7531:** {s.scoring_reason_zh}")
            st.markdown(f"**\u9700\u6c42\u7ec4\u6458\u8981:** {s.group_summary_zh}")

            st.markdown("---")
            st.caption("\u4eba\u5de5\u590d\u6838\uff08\u4e0d\u4fee\u6539\u8bc4\u5206\u6587\u4ef6\uff09")
            review_col1, review_col2, review_col3, review_col4 = st.columns(4)
            with review_col1:
                if st.button("\u2705 \u8bc4\u5206\u5408\u7406", key=f"ok_{s.truth_score_id}"):
                    submit_truth_review(s.truth_score_id, s.source_group_id, "score_reasonable")
                    st.success("\u5df2\u8bb0\u5f55")
                if st.button("\u2b06\ufe0f \u5206\u6570\u504f\u4f4e", key=f"low_{s.truth_score_id}"):
                    submit_truth_review(s.truth_score_id, s.source_group_id, "score_too_low")
                    st.success("\u5df2\u8bb0\u5f55")
            with review_col2:
                if st.button("\u2b07\ufe0f \u5206\u6570\u504f\u9ad8", key=f"high_{s.truth_score_id}"):
                    submit_truth_review(s.truth_score_id, s.source_group_id, "score_too_high")
                    st.success("\u5df2\u8bb0\u5f55")
                if st.button("\U0001f9fe \u8bc1\u636e\u4e0d\u597d", key=f"ev_{s.truth_score_id}"):
                    submit_truth_review(s.truth_score_id, s.source_group_id, "bad_evidence")
                    st.success("\u5df2\u8bb0\u5f55")
            with review_col3:
                if st.button("\U0001f465 \u7528\u6237\u753b\u50cf\u4e0d\u6e05", key=f"persona_{s.truth_score_id}"):
                    submit_truth_review(s.truth_score_id, s.source_group_id, "bad_persona")
                    st.success("\u5df2\u8bb0\u5f55")
                if st.button("\U0001f50d \u9700\u8981\u66f4\u591a\u8bc1\u636e", key=f"needev_{s.truth_score_id}"):
                    submit_truth_review(s.truth_score_id, s.source_group_id, "needs_more_evidence")
                    st.success("\u5df2\u8bb0\u5f55")
            with review_col4:
                if st.button("\U0001f6ab \u5e94\u4e22\u5f03", key=f"discard_{s.truth_score_id}"):
                    submit_truth_review(s.truth_score_id, s.source_group_id, "should_discard")
                    st.success("\u5df2\u8bb0\u5f55")
                if st.button("\u27a1\ufe0f \u53ef\u8fdb Fit Scoring", key=f"fit_{s.truth_score_id}"):
                    submit_truth_review(s.truth_score_id, s.source_group_id, "should_enter_fit_scoring")
                    st.success("\u5df2\u8bb0\u5f55")



def _render_evidence_gap_page() -> None:
    """Render Stage 3.2 Evidence Gap Analysis tab."""
    st.header("证据缺口分析 (Stage 3.2 Evidence Gap Analysis)")
    gaps = get_gap_analyses()
    plans = get_collection_plans()
    plan_by_gap = {p.gap_analysis_id: p for p in plans}

    if not gaps:
        st.info("暂无证据缺口分析。请先运行: demand-radar run-stage32 --source calibrated_llm")
        return

    by_pri = {"high": 0, "medium": 0, "low": 0}
    total_signals = sum(p.target_new_signals for p in plans)
    for g in gaps:
        by_pri[g.priority] = by_pri.get(g.priority, 0) + 1

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("分析候选数", len(gaps))
    c2.metric("🔴 高优先级", by_pri["high"])
    c3.metric("🟡 中优先级", by_pri["medium"])
    c4.metric("🎯 目标新增信号", total_signals)
    st.divider()

    PRI_EMOJI = {"high": "🔴", "medium": "🟡", "low": "🟢"}

    for g in sorted(gaps, key=lambda x: (x.priority != "high", x.priority != "medium", -x.current_truth_score)):
        emoji = PRI_EMOJI.get(g.priority, "")
        plan = plan_by_gap.get(g.gap_analysis_id)
        with st.expander(f"{emoji} {g.group_title_zh} | {g.current_truth_score:.1f}分 | {g.priority} priority"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Truth Score:** {g.current_truth_score:.1f} / 100")
                st.markdown(f"**Truth Level:** {g.current_truth_level}")
                st.markdown(f"**Next Action:** {g.current_next_action}")
                st.markdown(f"**Priority:** {emoji} {g.priority}")
                st.markdown("**Main Bottleneck Dimensions:**")
                for b in g.main_bottleneck_dimensions:
                    score = g.dimension_scores.get(b, 0)
                    st.markdown(f"  - {b}: {score:.1f}")
            with col2:
                st.markdown("**Missing Evidence Types:**")
                for m in g.missing_evidence_types:
                    st.markdown(f"  - `{m}`")
                st.markdown(f"**Target New Signals:** {g.target_new_signals}")

            st.markdown(f"**Gap Reason:** {g.gap_reason_zh}")
            st.markdown(f"**Upgrade Path:** {g.upgrade_path_zh}")

            if plan:
                st.markdown("---")
                st.markdown("**采集计划:**")
                if plan.search_keywords_zh:
                    st.markdown("中文关键词: " + " | ".join(plan.search_keywords_zh[:4]))
                if plan.search_keywords_en:
                    st.markdown("EN keywords: " + " | ".join(plan.search_keywords_en[:3]))
                if plan.target_source_types:
                    st.markdown("目标来源: " + ", ".join(plan.target_source_types[:4]))
                st.markdown(f"**采集建议:** {plan.collection_notes_zh}")
                st.markdown(f"**预期效果:** {plan.expected_impact_zh}")


def _render_targeted_expansion_page() -> None:
    """Stage 3.3: Targeted Evidence Expansion tab."""
    st.header("定向证据扩展")
    summary = get_expansion_summary()
    if summary is None:
        st.info("尚未运行 Stage 3.3。请执行 demand-radar run-stage33 生成模板。")
        st.markdown("**运行命令：**")
        st.code("demand-radar build-targeted-signal-template\ndemand-radar run-stage33")
        return

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("模板行数", summary.template_rows)
    col2.metric("有效信号", summary.valid_signals)
    col3.metric("告警信号", summary.warning_signals)
    col4.metric("无效信号", summary.invalid_signals)

    col5, col6, col7 = st.columns(3)
    col5.metric("合并输入行", summary.combined_input_rows)
    col6.metric("基础样本", summary.base_rows)
    col7.metric("新增定向信号", summary.targeted_rows_included)

    if summary.excluded_synthetic > 0:
        st.warning(f"已排除 synthetic 信号: {summary.excluded_synthetic} 条")

    st.markdown("---")

    # Validation details
    validations = get_targeted_validations()
    if validations:
        st.subheader("信号验证详情")
        by_group: dict = {}
        for v in validations:
            gid = v.target_group_id or "unknown"
            by_group.setdefault(gid, {"valid": 0, "warning": 0, "invalid": 0, "excluded": 0})
            by_group[gid][v.status] = by_group[gid].get(v.status, 0) + 1

        for gid, counts in by_group.items():
            total = sum(counts.values())
            with st.expander(f"候选: {gid} | 共 {total} 条"):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("✅ 有效", counts.get("valid", 0))
                c2.metric("⚠️ 告警", counts.get("warning", 0))
                c3.metric("❌ 无效", counts.get("invalid", 0))
                c4.metric("⛔ 排除", counts.get("excluded", 0))

                invalid_items = [v for v in validations if (v.target_group_id or "unknown") == gid and v.status == "invalid"]
                if invalid_items:
                    st.markdown("**无效原因：**")
                    for item in invalid_items[:5]:
                        if item.validation_errors:
                            st.markdown(f"- `{item.target_signal_id}`: {'; '.join(item.validation_errors)}")

    # Truth score delta
    deltas = get_truth_score_deltas()
    if deltas:
        st.markdown("---")
        st.subheader("Truth Score 对比（前后）")
        for delta in deltas:
            before = delta.before_truth_score
            after = delta.after_truth_score
            change = delta.delta
            level_change = f"{delta.before_truth_level} → {delta.after_truth_level}" if delta.before_truth_level else "N/A"
            with st.expander(f"{delta.group_title_zh} | {before:.1f} → {after:.1f} (Δ {change:+.1f})" if before is not None and after is not None else delta.group_title_zh):
                col_a, col_b, col_c = st.columns(3)
                col_a.metric("扩展前", f"{before:.1f}" if before is not None else "N/A")
                col_b.metric("扩展后", f"{after:.1f}" if after is not None else "N/A", delta=f"{change:+.1f}" if change is not None else None)
                col_c.metric("级别变化", level_change)
                if delta.improved_dimensions:
                    st.markdown("改善维度: " + ", ".join(delta.improved_dimensions))
                if delta.remaining_gaps:
                    st.markdown("剩余缺口: " + ", ".join(delta.remaining_gaps))
    else:
        st.info("尚无 Truth Score 对比数据。完整重跑后可查看。")


def _render_lineage_page() -> None:
    """Stage 3.4: Candidate Lineage & Targeted Evidence Attribution tab."""
    st.header("候选谱系追踪")

    lineages = get_candidate_lineages()
    attributions = get_targeted_evidence_attributions()
    stable_deltas = get_stable_truth_score_deltas()

    if not lineages and not attributions:
        st.info("尚未运行 Stage 3.4。请执行 demand-radar run-stage34。")
        st.code("demand-radar run-stage34")
        return

    # Summary metrics
    from collections import Counter
    sc = Counter(l.match_strength for l in lineages)
    ac = Counter(a.attribution_status for a in attributions)
    total_attr = len(attributions)
    attributed = (
        ac.get("attributed_to_expected_group", 0) + ac.get("attributed_to_related_group", 0)
    )
    attr_rate = attributed / total_attr if total_attr else 0.0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("候选谱系", len(lineages))
    col2.metric("强匹配", sc.get("strong", 0))
    col3.metric("弱匹配", sc.get("weak", 0))
    col4.metric("证据归因率", f"{attr_rate:.0%}")

    col5, col6, col7 = st.columns(3)
    col5.metric("分裂候选", sc.get("split", 0))
    col6.metric("合并候选", sc.get("merged", 0))
    col7.metric("无基线", sc.get("missing_baseline", 0))

    st.markdown("---")

    # Stable delta section
    if stable_deltas:
        st.subheader("稳定 Truth Score Delta")
        dc = Counter(d.delta_confidence for d in stable_deltas)
        c1, c2, c3 = st.columns(3)
        c1.metric("高置信", dc.get("high", 0))
        c2.metric("中置信", dc.get("medium", 0))
        c3.metric("低置信", dc.get("low", 0))

        for delta in sorted(stable_deltas, key=lambda d: -(d.stable_delta or 0)):
            delta_str = f"+{delta.stable_delta:.1f}" if delta.stable_delta and delta.stable_delta > 0 else (
                f"{delta.stable_delta:.1f}" if delta.stable_delta is not None else "N/A"
            )
            title = delta.before_group_title_zh or delta.after_group_title_zh or delta.stable_delta_id
            conf_emoji = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(delta.delta_confidence, "⚪")
            with st.expander(f"{conf_emoji} {title[:55]} | Δ {delta_str} [{delta.delta_confidence}]"):
                col_a, col_b, col_c = st.columns(3)
                col_a.metric("扩展前", f"{delta.before_truth_score:.1f}" if delta.before_truth_score else "N/A",
                             delta=None)
                col_b.metric("扩展后", f"{delta.after_truth_score:.1f}" if delta.after_truth_score else "N/A",
                             delta=delta_str if delta.stable_delta else None)
                col_c.metric("置信度", delta.delta_confidence)
                st.markdown(f"**解释:** {delta.interpretation_zh}")
                st.markdown(f"**建议:** `{delta.recommended_next_action}`")
                if delta.drift_flags:
                    st.warning("漂移标记: " + ", ".join(delta.drift_flags))
                if delta.delta_confidence == "low":
                    st.error("⚠️ 低置信 delta 不应用于 Stage 4 决策")

    st.markdown("---")

    # Lineage cards
    if lineages:
        st.subheader("候选谱系详情")
        for lin in lineages:
            strength_emoji = {
                "strong": "💚", "weak": "💛", "split": "🟠",
                "merged": "🔵", "unmatched": "❌", "missing_baseline": "🆕"
            }.get(lin.match_strength, "⚪")
            title = lin.before_group_title_zh or lin.after_group_title_zh or lin.lineage_id
            with st.expander(f"{strength_emoji} {title[:55]} | score={lin.match_score:.2f} [{lin.match_strength}]"):
                if lin.before_group_id:
                    st.markdown(f"**Before:** {lin.before_group_title_zh} | {lin.before_truth_score} [{lin.before_truth_level}]")
                if lin.after_group_id:
                    st.markdown(f"**After:** {lin.after_group_title_zh} | {lin.after_truth_score} [{lin.after_truth_level}]")
                if lin.match_reasons:
                    st.markdown("**匹配原因:** " + " / ".join(lin.match_reasons))
                if lin.drift_flags:
                    st.warning("漂移: " + ", ".join(lin.drift_flags))
                if lin.targeted_signal_ids:
                    st.markdown(
                        f"定向信号: {len(lin.targeted_signal_ids)} 条 | "
                        f"已归入: {len(lin.matched_targeted_signal_ids)} | "
                        f"未归入: {len(lin.unmatched_targeted_signal_ids)}"
                    )
                st.info(lin.lineage_summary_zh)

    # Attribution section
    if attributions:
        st.markdown("---")
        st.subheader("定向证据归因")
        lost = ac.get("lost_in_extraction", 0) + ac.get("lost_in_clustering", 0) + ac.get("lost_in_merge", 0)
        c1, c2, c3 = st.columns(3)
        c1.metric("归因至预期组", ac.get("attributed_to_expected_group", 0))
        c2.metric("归因至相关组", ac.get("attributed_to_related_group", 0))
        c3.metric("在各阶段丢失", lost)
        if total_attr:
            st.progress(attr_rate, text=f"归因率: {attr_rate:.0%}")




def _render_real_evidence_page() -> None:
    """Render the Real Evidence Calibration tab."""
    import streamlit as st
    from demand_radar.ui.real_evidence_service import (
        get_real_evidence_summary,
        get_real_evidence_items,
        get_real_evidence_validations,
        get_calibration_reviews,
    )
    from demand_radar.real_evidence.real_evidence_store import append_calibration_review
    from demand_radar.real_evidence.real_evidence_schema import CalibrationReview
    from demand_radar.state.raw_store import next_ids, utc_now_iso

    st.subheader("真实证据校准 (Stage R1)")

    summary = get_real_evidence_summary()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("证据条数", summary["evidence_items"])
    col2.metric("有效", summary["valid"])
    col3.metric("告警", summary["warning"])
    col4.metric("无效", summary["invalid"])

    col5, col6, col7 = st.columns(3)
    col5.metric("用户声音信号", summary["user_voice_signals"])
    col6.metric("付费/成本信号", summary["paid_or_cost_signals"])
    col7.metric("替代方案信号", summary["workaround_signals"])

    if summary["evidence_items"] == 0:
        st.info(
            "真实证据包尚未填写。"
            " 请先运行: demand-radar build-real-evidence-template"
            " 然后填写: examples/real_evidence_pack_ai_investment_tracking.csv"
            " 再运行: demand-radar run-stage-r1"
        )
        return

    st.markdown("---")

    items = get_real_evidence_items()
    validations = get_real_evidence_validations()
    val_map = {v["evidence_id"]: v for v in validations}

    review_labels = [
        "true_pain", "fake_pain", "too_generic", "weak_signal", "strong_signal",
        "commercial_signal", "not_commercial", "bad_extraction", "bad_merge",
        "missed_pain", "duplicate_noise",
    ]
    label_display = {
        "true_pain": "真痛点",
        "fake_pain": "假痛点",
        "too_generic": "太泛",
        "weak_signal": "弱信号",
        "strong_signal": "强信号",
        "commercial_signal": "有商业化可能",
        "not_commercial": "无商业化可能",
        "bad_extraction": "抽取错误",
        "bad_merge": "合并错误",
        "missed_pain": "漏掉痛点",
        "duplicate_noise": "噪音/重复",
    }

    st.subheader(f"证据列表 ({len(items)} 条)")
    for item in items:
        val = val_map.get(item["evidence_id"], {})
        status = val.get("status", "unknown")
        status_emoji = {"valid": "✅", "warning": "⚠️", "invalid": "❌", "excluded": "⏐"}.get(status, "?")
        with st.expander(
            f"{status_emoji} [{item['source_type']}] {item.get('title') or item['evidence_id'][:60]}"
        ):
            st.markdown(f"**Source:** {item.get('source_url') or item.get('source_note') or 'N/A'}")
            st.markdown(f"**Persona:** {item.get('persona') or 'N/A'} | **Stage:** {item.get('workflow_stage') or 'N/A'}")
            st.markdown(f"**Pain type:** {item.get('pain_type') or 'N/A'}")
            if item.get("evidence_quote"):
                st.info(f"引文: {item['evidence_quote'][:200]}")
            if item.get("raw_text"):
                st.text_area("原文", item["raw_text"][:500], height=80, key=f"rt_{item['evidence_id']}", disabled=True)

            selected = st.multiselect(
                "人工标注",
                options=review_labels,
                format_func=lambda x: label_display.get(x, x),
                key=f"labels_{item['evidence_id']}",
            )
            note = st.text_input("备注", key=f"note_{item['evidence_id']}")
            if st.button("提交标注", key=f"submit_{item['evidence_id']}"):
                if selected:
                    review_id = next_ids("calibration_review", 1)[0]
                    review = CalibrationReview(
                        review_id=review_id,
                        evidence_id=item["evidence_id"],
                        human_labels=selected,
                        reviewer_note_zh=note or None,
                        created_at=utc_now_iso(),
                    )
                    append_calibration_review(review)
                    st.success(f"已提交标注: {selected}")
                else:
                    st.warning("请选择至少一个标签。")

    if summary["calibration_reviews"] > 0:
        st.markdown("---")
        st.subheader(f"校准 Review 记录 ({summary['calibration_reviews']} 条)")
        reviews = get_calibration_reviews()
        for r in reviews[-10:]:
            st.markdown(f"- `{r['evidence_id']}` {r['human_labels']} {r.get('reviewer_note_zh') or ''}")


def _render_acquisition_page() -> None:
    import streamlit as st
    from demand_radar.ui.acquisition_service import get_acquisition_summary, get_evidence_candidates

    st.subheader("自动采集 (MVP-A)")
    summary = get_acquisition_summary()

    if summary["last_run_id"] is None:
        st.info("尚未运行采集。请先运行: demand-radar run-acquisition --domain ai_investment_tracking")
        return

    st.caption("Run ID: " + str(summary["last_run_id"]))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("原始信号", summary["raw_signal_count"])
    c2.metric("去重后", summary["unique_signal_count"])
    c3.metric("重复", summary["duplicate_count"])
    c4.metric("候选总数", summary["evidence_candidate_count"])

    c5, c6, c7 = st.columns(3)
    c5.metric("有效候选", summary["valid_candidate_count"])
    c6.metric("告警候选", summary["warning_candidate_count"])
    c7.metric("无效候选", summary["invalid_candidate_count"])

    if summary["by_source"]:
        st.markdown("**来源分布**")
        for src, cnt in summary["by_source"].items():
            st.write("- " + str(src) + ": " + str(cnt))

    if summary["errors"]:
        with st.expander("错误", expanded=False):
            for e in summary["errors"]:
                st.error(e)

    if summary["warnings"]:
        with st.expander("告警", expanded=False):
            for w in summary["warnings"]:
                st.warning(w)

    candidates = get_evidence_candidates()
    valid_cands = [c for c in candidates if c.get("validation_status") == "valid"]
    if valid_cands:
        st.markdown("**Top 有效候选 (共 " + str(len(valid_cands)) + " 条)**")
        for cand in valid_cands[:30]:
            label = (cand.get("title") or cand.get("source_url") or "(无标题)")[:80]
            with st.expander(label):
                st.write("来源类型: " + str(cand.get("source_type", "-")))
                if cand.get("source_url"):
                    st.write("URL: " + cand["source_url"])
                st.write("状态: " + str(cand.get("validation_status", "-")))
                sigs = cand.get("detected_signal_types", [])
                if sigs:
                    st.write("信号类型: " + ", ".join(sigs))
                raw = cand.get("raw_text", "")
                if raw:
                    st.caption(raw[:300])


def _render_mvp_b_page() -> None:
    import streamlit as st
    from demand_radar.mvp_b.mvp_b_store import load_relevance_dicts, load_pain_dicts

    st.subheader("MVP-B 痛点抽取")

    rel_results = load_relevance_dicts()
    pain_items = load_pain_dicts()

    if not rel_results:
        st.info("尚未运行 MVP-B。请先运行: demand-radar run-mvp-b --domain ai_investment_tracking")
        return

    include_ct = sum(1 for r in rel_results if r.get("relevance_decision") == "include")
    uncertain_ct = sum(1 for r in rel_results if r.get("relevance_decision") == "uncertain")
    exclude_ct = sum(1 for r in rel_results if r.get("relevance_decision") == "exclude")

    c1, c2, c3 = st.columns(3)
    c1.metric("领域相关 (include)", include_ct)
    c2.metric("不确定 (uncertain)", uncertain_ct)
    c3.metric("域外排除 (exclude)", exclude_ct)

    if pain_items:
        extract_ct = sum(1 for p in pain_items if p.get("should_extract"))
        strong_ct = sum(1 for p in pain_items if p.get("evidence_strength") == "strong")
        medium_ct = sum(1 for p in pain_items if p.get("evidence_strength") == "medium")
        reject_ct = sum(1 for p in pain_items if p.get("evidence_strength") == "reject")

        c4, c5, c6, c7 = st.columns(4)
        c4.metric("抽取成功", extract_ct)
        c5.metric("强信号", strong_ct)
        c6.metric("中信号", medium_ct)
        c7.metric("拒绝", reject_ct)

        top_pains = sorted(
            [p for p in pain_items if p.get("should_extract") and p.get("evidence_strength") in ("strong", "medium")],
            key=lambda x: (x.get("evidence_strength") == "strong", x.get("confidence", 0)),
            reverse=True,
        )[:20]

        if top_pains:
            st.markdown("**Top 痛点信号**")
            for item in top_pains:
                title = item.get("title") or item.get("candidate_id") or ""
                strength_label = "[" + str(item.get("evidence_strength", "-")) + "] " + str(title)[:80]
                with st.expander(strength_label):
                    st.write("Persona: " + str(item.get("persona", "-")))
                    st.write("Workflow: " + str(item.get("workflow_stage", "-")))
                    st.write("Pain Type: " + str(item.get("pain_type", "-")))
                    if item.get("pain_description_zh"):
                        st.write("痛点: " + item["pain_description_zh"])
                    if item.get("evidence_quote"):
                        st.caption("原文证据: " + item["evidence_quote"][:300])
                    st.write("商业信号: " + str(item.get("commercial_signal_type", "-")))
                    st.write("置信度: " + str(round(item.get("confidence", 0), 2)))
                    if item.get("source_url"):
                        st.write("URL: " + item["source_url"])
