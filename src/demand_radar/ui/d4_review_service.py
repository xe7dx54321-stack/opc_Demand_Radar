"""D4 second-round review report builder."""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from demand_radar.state.raw_store import utc_now_iso
from demand_radar.ui.current_task_service import D4_PAIN_PATH, load_d4_pain_signals
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
        "# D4 Second Round Review Report",
        "",
        f"Generated: {utc_now_iso()}",
        "",
        "## Summary",
        f"- total_pain_signals: {len(signals)}",
        f"- reviewed_count: {len(reviews)}",
        f"- unreviewed_count: {len(unreviewed)}",
        f"- true_pain_count: {summary['true_pain']}",
        f"- false_pain_count: {summary['false_pain']}",
        f"- uncertain_count: {summary['uncertain']}",
        f"- commercial_high: {summary['commercial_high']}",
        f"- commercial_medium: {summary['commercial_medium']}",
        f"- commercial_low: {summary['commercial_low']}",
        f"- commercial_unclear: {summary['commercial_unclear']}",
        "",
        "## Action Decisions",
        f"- pursue: {summary['pursue']}",
        f"- watch: {summary['watch']}",
        f"- reject: {summary['reject']}",
        f"- needs_more_evidence: {summary['needs_more_evidence']}",
        "",
        "## Top Reject Reasons",
    ]
    if error_labels:
        lines.extend(f"- {label}: {count}" for label, count in error_labels.most_common(10))
    else:
        lines.append("- none")

    if pursue:
        lines += ["", "## Top Pursue Candidates", ""]
        for review in pursue[:10]:
            signal = signal_map.get(review.pain_item_id, {})
            title = signal.get("title") or review.pain_item_id
            lines += [
                f"- **{str(title)[:100]}**",
                f"  - pain_item_id: {review.pain_item_id}",
                f"  - source: {str(signal.get('source_url') or review.source_url or '')[:120]}",
                f"  - commercial: {review.commercial_potential}",
                f"  - note: {review.reviewer_note_zh or ''}",
            ]

    if watch:
        lines += ["", "## Top Watch Candidates", ""]
        for review in watch[:10]:
            signal = signal_map.get(review.pain_item_id, {})
            title = signal.get("title") or review.pain_item_id
            lines.append(
                f"- **{str(title)[:100]}** | pain_item_id: {review.pain_item_id} "
                f"| commercial: {review.commercial_potential}"
            )

    if reject:
        lines += ["", "## Rejected Signals", ""]
        for review in reject[:10]:
            signal = signal_map.get(review.pain_item_id, {})
            title = signal.get("title") or review.pain_item_id
            reason = ", ".join(review.error_labels) if review.error_labels else (
                review.reviewer_note_zh or "no reason"
            )
            lines.append(f"- {str(title)[:100]} | pain_item_id: {review.pain_item_id} | {reason}")

    if unreviewed:
        lines += ["", "## Unreviewed Signals (pending)", ""]
        for signal in unreviewed[:20]:
            lines.append(
                f"- {str(signal.get('title', '?'))[:100]} | "
                f"{signal.get('evidence_strength')} | {str(signal.get('source_url', ''))[:90]}"
            )

    text = "\n".join(lines) + "\n"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(text, encoding="utf-8")
    return text
