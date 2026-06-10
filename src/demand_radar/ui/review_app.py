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
    ("Good", "good_extraction"),
    ("Weak", "weak_extraction"),
    ("False Positive", "false_positive"),
    ("False Negative", "false_negative"),
    ("Bad Quote", "bad_quote"),
    ("Bad Persona", "bad_persona"),
    ("Bad Pain Description", "bad_pain_description"),
    ("Missing Payment Signal", "missing_payment_signal"),
    ("Missing Workaround", "missing_workaround"),
    ("Should Quarantine", "should_quarantine"),
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


def main() -> None:
    st.set_page_config(page_title="Demand Radar Review", layout="wide")
    st.title("Demand Radar Review")
    st.caption(
        "Local calibration review UI. Reviews are appended as feedback memory "
        "and never mutate raw or pain point state."
    )

    items = load_review_items()
    summary = get_review_summary(items)
    _render_summary(summary)

    if st.button("Rebuild Calibration Report", type="primary"):
        rebuilt = build_calibration_report()
        st.success(
            "Calibration report rebuilt successfully "
            f"(reviews={rebuilt.calibration_reviews}, pain_points={rebuilt.pain_points})."
        )

    filters = _sidebar_filters(items)
    filtered_items = _filter_items(items, filters)
    st.caption(f"Showing {len(filtered_items)} of {len(items)} review items.")

    for item in filtered_items:
        _render_item(item)


def _render_summary(summary: object) -> None:
    labels = summary.labels
    metric_values = [
        ("Raw signals", summary.raw_signals),
        ("Normalized", summary.normalized_signals),
        ("Pain points", summary.pain_points),
        ("Quarantine", summary.quarantine),
        ("Reviewed", summary.reviewed),
        ("Unreviewed", summary.unreviewed),
        ("Good", labels.get("good_extraction", 0)),
        ("Weak", labels.get("weak_extraction", 0)),
        ("False positive", labels.get("false_positive", 0)),
        ("False negative", labels.get("false_negative", 0)),
        ("Bad quote", labels.get("bad_quote", 0)),
        ("Bad persona", labels.get("bad_persona", 0)),
        ("Should quarantine", labels.get("should_quarantine", 0)),
    ]
    columns = st.columns(7)
    for index, (label, value) in enumerate(metric_values):
        columns[index % len(columns)].metric(label, value)


def _sidebar_filters(items: list[ReviewItem]) -> dict[str, object]:
    with st.sidebar:
        st.header("Filters")
        review_range = st.radio("View range", REVIEW_RANGES, index=1)
        label_options = ["All", *sorted(VALID_REVIEW_LABELS)]
        label = st.selectbox("Review label", label_options)
        persona = st.selectbox("Persona", PERSONAS)
        source_types = ["All", *_unique_values(item.source_type for item in items)]
        source_type = st.selectbox("Source type", source_types)
        languages = ["All", *_unique_values(item.language for item in items)]
        language = st.selectbox("Language", languages)
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
    title = f"{item.title} - {item.item_type}"
    with st.expander(title, expanded=not item.reviewed):
        _render_metadata(item)
        left, right = st.columns([3, 2])
        with left:
            st.subheader("Signal Text")
            st.markdown("**Raw text**")
            st.text_area("Raw text", item.raw_text or "", height=140, label_visibility="collapsed", disabled=True)
            st.markdown("**Normalized text**")
            _render_normalized_text(item)
        with right:
            st.subheader("Extraction")
            _render_extraction_fields(item)
            _render_review_status(item)
            _render_quarantine(item)
        _render_review_controls(item)


def _render_metadata(item: ReviewItem) -> None:
    metadata = [
        f"raw_signal_id: `{item.raw_signal_id}`",
        f"normalized_signal_id: `{item.normalized_signal_id or ''}`",
        f"pain_point_id: `{item.pain_point_id or ''}`",
        f"source: `{item.source_name or ''}` / `{item.source_type or ''}`",
        f"language: `{item.language or ''}`",
        f"domain_tags: `{', '.join(item.domain_tags)}`",
    ]
    st.markdown("  \n".join(metadata))
    if item.url:
        st.markdown(f"Source URL: [{item.url}]({item.url})")


def _render_normalized_text(item: ReviewItem) -> None:
    text = item.normalized_text or ""
    quote = (item.evidence_quote or "").strip()
    if quote and evidence_quote_found(item):
        st.markdown(_highlight_quote(text, quote), unsafe_allow_html=True)
    elif quote:
        st.warning("Evidence quote not found in normalized text")
        st.text_area("Normalized text", text, height=180, label_visibility="collapsed", disabled=True)
    else:
        st.text_area("Normalized text", text, height=180, label_visibility="collapsed", disabled=True)


def _render_extraction_fields(item: ReviewItem) -> None:
    rows = [
        ("Persona", item.persona),
        ("Scenario", item.scenario),
        ("Job to be done", item.job_to_be_done),
        ("Pain", item.pain_description),
        ("Current workaround", item.current_workaround),
        ("Frequency signal", item.frequency_signal),
        ("Payment signal", item.payment_signal),
        ("Confidence", f"{item.confidence:.2f}" if item.confidence is not None else None),
    ]
    for label, value in rows:
        st.markdown(f"**{label}:** {value or ''}")
    if item.evidence_quote:
        st.markdown("**Evidence quote:**")
        st.info(item.evidence_quote)


def _render_review_status(item: ReviewItem) -> None:
    if item.reviewed:
        st.success(f"Reviewed: {item.latest_review_label}")
        st.caption(item.latest_review_note or "")
    else:
        st.warning("Unreviewed")


def _render_quarantine(item: ReviewItem) -> None:
    if item.item_type != "quarantine":
        return
    st.error(f"Quarantine reason: {item.quarantine_reason}")
    with st.expander("Quarantine payload"):
        st.json(item.quarantine_payload or {})


def _render_review_controls(item: ReviewItem) -> None:
    key_base = _item_key(item)
    with st.form(f"review_form_{key_base}", clear_on_submit=False):
        note = st.text_area("Reviewer note", key=f"note_{key_base}")
        col_a, col_b, col_c = st.columns(3)
        expected_persona = col_a.text_input("Expected persona", key=f"persona_{key_base}")
        expected_quote = col_b.text_input("Expected evidence quote", key=f"quote_{key_base}")
        expected_pain = col_c.text_input("Expected pain description", key=f"pain_{key_base}")
        st.markdown("**Review action**")
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
        reviewer_note=note.strip() or f"Marked as {label}",
        expected_persona=expected_persona.strip() or None,
        expected_evidence_quote=expected_quote.strip() or None,
        expected_pain_description=expected_pain.strip() or None,
        should_be_quarantined=True if label == "should_quarantine" else None,
    )
    st.success(f"Saved review: {label}")
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


if __name__ == "__main__":
    main()
