"""D4 第二轮人工审核报告生成器。"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from demand_radar.state.raw_store import utc_now_iso
from demand_radar.ui.current_task_service import D4_PAIN_PATH, load_d4_pain_signals
from demand_radar.ui.d4_chinese_labels import commercial_label, error_label, strength_label
from demand_radar.ui.d4_review_store import D4ReviewStore

DEFAULT_D4_REVIEW_REPORT_PATH = Path("outputs/reviews/d4_second_review_report.md")


def build_d4_review_report(
    store: D4ReviewStore | None = None,
    output_path: Path | None = None,
    pain_items_path: Path | str | None = None,
) -> str:
    store = store or D4ReviewStore()
    report_path = output_path or DEFAULT_D4_REVIEW_REPORT_PATH

    signals = load_d4_pain_signals(pain_items_path or D4_PAIN_PATH)
    reviews = store.load_reviews()
    summary = store.summary()

    reviewed_ids = {review.pain_item_id for review in reviews}
    unreviewed = [signal for signal in signals if signal.get("pain_item_id") not in reviewed_ids]
    signal_map = {str(signal.get("pain_item_id")): signal for signal in signals}

    pursue = [review for review in reviews if review.action_decision == "pursue"]
    watch = [review for review in reviews if review.action_decision == "watch"]
    reject = [review for review in reviews if review.action_decision == "reject"]
    error_labels = Counter(label for review in reviews for label in review.error_labels)

    lines = [
        "# D4 第二轮人工审核报告",
        "",
        f"生成时间：{utc_now_iso()}",
        "",
        "## 汇总",
        f"- 痛点信号总数：{len(signals)}",
        f"- 已审核：{len(reviews)}",
        f"- 未审核：{len(unreviewed)}",
        f"- 真痛点：{summary['true_pain']}",
        f"- 非真痛点：{summary['false_pain']}",
        f"- 不确定：{summary['uncertain']}",
        f"- 高商业潜力：{summary['commercial_high']}",
        f"- 中商业潜力：{summary['commercial_medium']}",
        f"- 低商业潜力：{summary['commercial_low']}",
        f"- 商业潜力不明确：{summary['commercial_unclear']}",
        "",
        "## 处理决策",
        f"- 继续推进：{summary['pursue']}",
        f"- 观察：{summary['watch']}",
        f"- 拒绝：{summary['reject']}",
        f"- 需要更多证据：{summary['needs_more_evidence']}",
        "",
        "## 主要拒绝原因",
    ]
    if error_labels:
        lines.extend(f"- {error_label(label)}：{count}" for label, count in error_labels.most_common(10))
    else:
        lines.append("- 暂无")

    if pursue:
        lines += ["", "## 建议继续推进的候选", ""]
        for review in pursue[:10]:
            signal = signal_map.get(review.pain_item_id, {})
            title = signal.get("title") or review.pain_item_id
            lines += [
                f"- **{str(title)[:100]}**",
                f"  - 痛点编号：{review.pain_item_id}",
                f"  - 来源：{str(signal.get('source_url') or review.source_url or '')[:120]}",
                f"  - 商业潜力：{commercial_label(review.commercial_potential)}",
                f"  - 备注：{review.reviewer_note_zh or ''}",
            ]

    if watch:
        lines += ["", "## 建议观察的候选", ""]
        for review in watch[:10]:
            signal = signal_map.get(review.pain_item_id, {})
            title = signal.get("title") or review.pain_item_id
            lines.append(
                f"- **{str(title)[:100]}** | 痛点编号：{review.pain_item_id} "
                f"| 商业潜力：{commercial_label(review.commercial_potential)}"
            )

    if reject:
        lines += ["", "## 已拒绝信号", ""]
        for review in reject[:10]:
            signal = signal_map.get(review.pain_item_id, {})
            title = signal.get("title") or review.pain_item_id
            reason = (
                "，".join(error_label(label) for label in review.error_labels)
                if review.error_labels
                else (review.reviewer_note_zh or "未填写原因")
            )
            lines.append(f"- {str(title)[:100]} | 痛点编号：{review.pain_item_id} | {reason}")

    if unreviewed:
        lines += ["", "## 待审核信号", ""]
        for signal in unreviewed[:20]:
            lines.append(
                f"- {str(signal.get('title', '?'))[:100]} | "
                f"{strength_label(signal.get('evidence_strength'))} | {str(signal.get('source_url', ''))[:90]}"
            )

    text = "\n".join(lines) + "\n"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(text, encoding="utf-8")
    return text
