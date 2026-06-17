"""Rule-based theme labeling for D5."""
from __future__ import annotations

from collections import Counter
from typing import Any

from demand_radar.d5.evidence_weighting import evidence_quality, source_diversity


TITLE_HINTS = [
    ("deal sourcing", "项目来源与筛选自动化"),
    ("deal flow", "项目来源与筛选自动化"),
    ("screening", "项目来源与筛选自动化"),
    ("market research", "市场研究与竞争分析"),
    ("competitive analysis", "市场研究与竞争分析"),
    ("research report", "研究报告与输出自动化"),
    ("coverage", "投研研究工作流自动化"),
    ("financial modeling", "投研研究工作流自动化"),
    ("data collection", "投研研究工作流自动化"),
    ("research execution", "投研研究工作流自动化"),
    ("workflow fragmentation", "投研工作流碎片化"),
    ("information overload", "投研工作流碎片化"),
]


def label_theme(
    theme_key: str,
    evidence_items: list[dict[str, Any]],
    source_groups: list[dict[str, Any]],
    review_lookup: dict[str, dict[str, Any]],
    llm_client: Any | None = None,
) -> dict[str, Any]:
    """Return Chinese theme labels and a compact explanation.

    The first pass is rule-based. If a caller later wires in a real LLM client,
    the same function can be extended without changing the pipeline surface.
    """
    del llm_client  # reserved for future structured output
    workflow_group = theme_key
    persona_group = _mode([item.get("persona_group") for item in evidence_items]) or _derive_persona_group(evidence_items)
    pain_type_group = _mode([item.get("pain_type_group") for item in evidence_items]) or _derive_pain_type_group(evidence_items)

    title = _theme_title(workflow_group, pain_type_group)
    core_pain = _core_pain_summary(evidence_items)
    job_to_be_done = _best_text([item.get("job_to_be_done") for item in evidence_items]) or _job_fallback(workflow_group)
    workaround = _best_text([item.get("current_solution") for item in evidence_items])

    source_categories = Counter(str(group.get("source_category") or "unknown") for group in source_groups)
    unique_domains = len({str(group.get("result_domain") or "unknown") for group in source_groups})
    quotes = _unique_nonempty(
        [
            str(item.get("evidence_quote") or "")
            for item in evidence_items
        ]
    )
    source_urls = _unique_nonempty([str(group.get("source_url") or "") for group in source_groups])

    reviewed_pursue_count = sum(
        1
        for item in evidence_items
        if (review_lookup.get(str(item.get("pain_item_id") or "")) or {}).get("action_decision") == "pursue"
    )
    reviewed_watch_count = sum(
        1
        for item in evidence_items
        if (review_lookup.get(str(item.get("pain_item_id") or "")) or {}).get("action_decision") == "watch"
    )
    reviewed_needs_more_evidence_count = sum(
        1
        for item in evidence_items
        if (review_lookup.get(str(item.get("pain_item_id") or "")) or {}).get("action_decision")
        == "needs_more_evidence"
    )
    reviewed_reject_count = sum(
        1
        for item in evidence_items
        if (review_lookup.get(str(item.get("pain_item_id") or "")) or {}).get("action_decision") == "reject"
    )
    reviewed_positive_count = sum(
        1
        for item in evidence_items
        if (review_lookup.get(str(item.get("pain_item_id") or "")) or {}).get("true_pain") is True
    )

    first_hand = sum(
        1
        for item in evidence_items
        if str(item.get("source_category") or "") == "first_hand_community"
    )
    workaround_count = sum(
        1
        for item in evidence_items
        if str(item.get("source_category") or "") == "workaround_discussion"
    )
    marketing_count = sum(
        1
        for item in evidence_items
        if str(item.get("source_category") or "") in {"content_marketing", "vendor_blog"}
    )
    job_count = sum(
        1
        for item in evidence_items
        if str(item.get("source_category") or "") == "job_description"
    )

    strong_count = sum(1 for item in evidence_items if str(item.get("evidence_strength") or "") == "strong")
    medium_count = sum(1 for item in evidence_items if str(item.get("evidence_strength") or "") == "medium")
    weak_count = sum(1 for item in evidence_items if str(item.get("evidence_strength") or "") == "weak")
    commercial_potential = _commercial_potential(evidence_items, review_lookup)
    evidence_q = evidence_quality(strong_count, medium_count, weak_count)
    diversity = source_diversity(unique_domains)
    confidence = _confidence(
        strong_count=strong_count,
        medium_count=medium_count,
        first_hand_count=first_hand,
        unique_domain_count=unique_domains,
        reviewed_pursue_count=reviewed_pursue_count,
        reviewed_reject_count=reviewed_reject_count,
        source_categories=source_categories,
    )
    recommendation = _recommendation(
        strong_count=strong_count,
        medium_count=medium_count,
        unique_domain_count=unique_domains,
        first_hand_or_workaround_count=first_hand + workaround_count,
        reviewed_pursue_count=reviewed_pursue_count,
        reviewed_reject_count=reviewed_reject_count,
        commercial_potential=commercial_potential,
    )
    reason = _recommendation_reason(
        recommendation=recommendation,
        strong_count=strong_count,
        medium_count=medium_count,
        unique_domain_count=unique_domains,
        first_hand_count=first_hand,
        workaround_count=workaround_count,
        marketing_count=marketing_count,
        job_count=job_count,
        source_categories=source_categories,
        quotes=quotes,
    )
    return {
        "theme_title_zh": title,
        "persona_group": persona_group,
        "workflow_group": workflow_group,
        "pain_type_group": pain_type_group,
        "core_pain_zh": core_pain,
        "job_to_be_done_zh": job_to_be_done,
        "current_workaround_zh": workaround,
        "commercial_potential": commercial_potential,
        "evidence_quality": evidence_q,
        "source_diversity": diversity,
        "confidence": round(confidence, 2),
        "action_recommendation": recommendation,
        "recommendation_reason_zh": reason,
        "representative_quotes": quotes[:5],
        "representative_source_urls": source_urls[:5],
        "reviewed_positive_count": reviewed_positive_count,
        "reviewed_pursue_count": reviewed_pursue_count,
        "reviewed_watch_count": reviewed_watch_count,
        "reviewed_needs_more_evidence_count": reviewed_needs_more_evidence_count,
        "reviewed_reject_count": reviewed_reject_count,
        "first_hand_evidence_count": first_hand,
        "workaround_evidence_count": workaround_count,
        "marketing_or_vendor_evidence_count": marketing_count,
        "job_description_evidence_count": job_count,
    }


def _recommendation(
    strong_count: int,
    medium_count: int,
    unique_domain_count: int,
    first_hand_or_workaround_count: int,
    reviewed_pursue_count: int,
    reviewed_reject_count: int,
    commercial_potential: str,
) -> str:
    if reviewed_reject_count >= 2:
        return "reject"
    if (
        reviewed_pursue_count >= 1
        and unique_domain_count >= 2
        and strong_count + medium_count >= 3
        and first_hand_or_workaround_count >= 1
        and reviewed_reject_count == 0
    ):
        return "pursue_candidate"
    if strong_count + medium_count >= 2 and reviewed_reject_count == 0:
        if first_hand_or_workaround_count >= 1 or commercial_potential in {"high", "medium"}:
            return "watch"
        return "needs_more_evidence"
    return "needs_more_evidence"


def _recommendation_reason(
    recommendation: str,
    strong_count: int,
    medium_count: int,
    unique_domain_count: int,
    first_hand_count: int,
    workaround_count: int,
    marketing_count: int,
    job_count: int,
    source_categories: Counter[str],
    quotes: list[str],
) -> str:
    category_text = "、".join(f"{k}{v}" for k, v in source_categories.most_common(5))
    quote_text = "；".join(quotes[:2]) if quotes else "未发现可直接引用的原文"
    if recommendation == "pursue_candidate":
        return (
            f"该主题已有 {strong_count + medium_count} 条强/中证据，覆盖 {unique_domain_count} 个域名；"
            f"其中一手/替代方案证据 {first_hand_count + workaround_count} 条。"
            f"来源构成为：{category_text}。"
            f"代表性原文：{quote_text}"
        )
    if recommendation == "watch":
        return (
            f"该主题已有基本证据，但一手社区或 workaround 证据仍偏少。"
            f"来源构成为：{category_text}。"
            f"其中营销/招聘类辅助证据 {marketing_count + job_count} 条。"
            f"代表性原文：{quote_text}"
        )
    if recommendation == "reject":
        return f"当前证据不足或出现明显反例，暂不建议继续推进。代表性原文：{quote_text}"
    return (
        f"当前更像是辅助证据或单点线索，仍需补充一手社区/替代方案证据。"
        f"来源构成为：{category_text}。"
        f"代表性原文：{quote_text}"
    )


def _theme_title(workflow_group: str, pain_type_group: str) -> str:
    if "项目来源" in workflow_group or "筛选" in workflow_group:
        return "项目来源与筛选自动化"
    if "市场研究" in workflow_group or "竞争分析" in workflow_group:
        return "市场研究与竞争分析"
    if "报告" in workflow_group or "memo" in workflow_group:
        return "研究报告与输出自动化"
    if "碎片化" in workflow_group or "信息过载" in workflow_group:
        return "投研工作流碎片化"
    if "组合监控" in workflow_group or "持续跟踪" in workflow_group:
        return "组合监控与持续跟踪"
    hints = [
        (("deal sourcing", "pipeline"), "项目来源与筛选自动化"),
        (("market research", "competitive"), "市场研究与竞争分析"),
        (("research report", "report"), "研究报告与输出自动化"),
        (("fragment", "overload", "workflow"), "投研工作流碎片化"),
        (("data", "research execution", "coverage", "financial"), "投研研究工作流自动化"),
    ]
    text = f"{workflow_group} {pain_type_group}".lower()
    for keys, title in hints:
        if all(key in text for key in keys):
            return title
    if "deal" in text or "sourcing" in text:
        return "项目来源与筛选自动化"
    if "market" in text or "competitive" in text:
        return "市场研究与竞争分析"
    if "report" in text or "memo" in text:
        return "研究报告与输出自动化"
    if "fragment" in text or "overload" in text:
        return "投研工作流碎片化"
    return "投研研究工作流自动化"


def _core_pain_summary(items: list[dict[str, Any]]) -> str:
    texts = _unique_nonempty(
        [str(item.get("pain_description_zh") or "") for item in items]
        + [str(item.get("job_to_be_done") or "") for item in items]
    )
    if not texts:
        return "该主题的核心痛点需要进一步从原始证据中提炼。"
    if len(texts) == 1:
        return texts[0][:220]
    return "；".join(texts[:2])[:260]


def _job_fallback(workflow_group: str) -> str:
    if "deal" in workflow_group or "项目来源" in workflow_group or "筛选" in workflow_group:
        return "更快发现、筛选和跟踪优质项目"
    if "market" in workflow_group or "市场研究" in workflow_group or "竞争分析" in workflow_group:
        return "更快完成市场研究与竞争分析"
    if "report" in workflow_group or "报告" in workflow_group or "memo" in workflow_group:
        return "更省时地生成研究报告和 memo"
    if "fragment" in workflow_group or "碎片化" in workflow_group:
        return "把分散工具和零碎流程收拢成统一工作流"
    if "组合监控" in workflow_group or "持续跟踪" in workflow_group:
        return "持续跟踪组合公司和市场变化，降低信息遗漏"
    return "提升投研工作流效率并减少手工处理"


def _best_text(values: list[Any]) -> str | None:
    items = _unique_nonempty([str(value or "") for value in values])
    return items[0] if items else None


def _unique_nonempty(values: list[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in out:
            out.append(text)
    return out


def _mode(values: list[Any]) -> str | None:
    counter = Counter(str(value) for value in values if value not in {None, "", "unknown"})
    if not counter:
        return None
    return counter.most_common(1)[0][0]


def _derive_persona_group(items: list[dict[str, Any]]) -> str | None:
    text = " ".join(str(item.get("persona") or "") for item in items).lower()
    if any(term in text for term in ["reddit", "individual investor", "value investing"]):
        return "个人投资者"
    if any(term in text for term in ["vc analyst", "pe analyst", "deal flow", "venture", "private equity", "investment banker"]):
        return "VC/PE/投行团队"
    if any(term in text for term in ["portfolio manager", "buy-side", "equity research", "investment researcher", "investment analyst"]):
        return "投研/股票研究团队"
    if "research" in text:
        return "研究型团队"
    return "相关用户"


def _derive_pain_type_group(items: list[dict[str, Any]]) -> str | None:
    text = " ".join(str(item.get("pain_type") or "") for item in items).lower()
    if any(term in text for term in ["fragment", "scattered", "overload"]):
        return "信息碎片化与工具分散"
    if any(term in text for term in ["manual", "time_cost", "inefficiency", "workflow"]):
        return "工作流效率与自动化"
    if any(term in text for term in ["skill gap", "capability"]):
        return "能力/工作流缺口"
    if any(term in text for term in ["report", "memo"]):
        return "报告与输出成本"
    return "工作流效率与自动化"

def _commercial_potential(items: list[dict[str, Any]], review_lookup: dict[str, dict[str, Any]]) -> str:
    values = []
    for item in items:
        review = review_lookup.get(str(item.get("pain_item_id") or ""))
        if review and review.get("commercial_potential"):
            values.append(str(review.get("commercial_potential")))
        elif item.get("commercial_potential"):
            values.append(str(item.get("commercial_potential")))
    counter = Counter(values)
    for choice in ["high", "medium", "unclear", "low"]:
        if counter.get(choice):
            return choice
    return "unclear"


def _confidence(
    strong_count: int,
    medium_count: int,
    first_hand_count: int,
    unique_domain_count: int,
    reviewed_pursue_count: int,
    reviewed_reject_count: int,
    source_categories: Counter[str],
) -> float:
    base = 0.35
    base += 0.1 * strong_count
    base += 0.06 * medium_count
    base += 0.05 * first_hand_count
    base += 0.04 * unique_domain_count
    base += 0.05 * reviewed_pursue_count
    base -= 0.06 * reviewed_reject_count
    if source_categories.get("first_hand_community"):
        base += 0.04
    if source_categories.get("workaround_discussion"):
        base += 0.03
    return max(0.1, min(0.95, base))
