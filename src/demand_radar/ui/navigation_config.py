"""Navigation config — defines the 5 top-level tabs and legacy history entries."""
from __future__ import annotations

# Top-level tab labels for the new consolidated UI
NAV_TABS = [
    "当前任务",
    "待审核队列",
    "需求证据结果",
    "诊断与历史",
    "设置与运行状态",
]

# Human-readable labels for history (diagnostic) sub-pages
HISTORY_PAGES = [
    ("痛点校准 (旧)", "pain_review"),
    ("需求主题审核 (旧)", "cluster_review"),
    ("合并建议 (旧)", "merge_review"),
    ("AI合并判断 (旧)", "ai_judge"),
    ("人工异常队列 (旧)", "exception"),
    ("LLM对比 (旧)", "llm_compare"),
    ("真实需求评分 (旧)", "truth_scoring"),
    ("证据缺口 (旧)", "evidence_gap"),
    ("定向证据扩展 (旧)", "targeted_expansion"),
    ("候选溯源 (旧)", "lineage"),
    ("Stage 3.5 定向验证 (旧)", "stage35"),
    ("真实证据校准 (旧)", "real_evidence"),
    ("自动采集 (旧)", "acquisition"),
    ("MVP-B 痛点抽取 (旧)", "mvp_b"),
    ("MVP-C 人工校准 (旧)", "mvp_c"),
    ("MVP-D 证据扩展 (旧)", "mvp_d"),
    ("MVP-D2 诊断校准 (旧)", "mvp_d2"),
    ("MVP-D3 搜索验证 (旧)", "mvp_d3"),
    ("MVP-D4 Foundation搜索 (参考)", "mvp_d4"),
    ("批次总览 (旧)", "batch"),
]

HISTORY_DISCLAIMER = (
    "📁 以下为历史诊断页，记录了系统各开发阶段的运行结果。"
    "这些页面**不是当前审核入口**，仅供参考。"
    "当前审核请使用「待审核队列」。"
)