"""Service layer for the local calibration review UI."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from demand_radar.calibration.calibration_schema import VALID_REVIEW_LABELS, CalibrationReview
from demand_radar.calibration.review_store import append_review, get_latest_review_for_item, load_reviews
from demand_radar.config.schemas import NormalizedSignal, PainPoint, QuarantineRecord, RawSignal
from demand_radar.state.processed_store import load_normalized_signals, load_pain_points
from demand_radar.state.quarantine_store import load_quarantine
from demand_radar.state.raw_store import load_raw_signals


class ReviewItem(BaseModel):
    raw_signal_id: str
    normalized_signal_id: str | None = None
    pain_point_id: str | None = None
    item_type: Literal["pain_point", "quarantine", "raw_only"]

    title: str
    raw_text: str | None = None
    normalized_text: str | None = None
    source_name: str | None = None
    source_type: str | None = None
    url: str | None = None
    language: str | None = None
    domain_tags: list[str] = Field(default_factory=list)
    batch_id: str | None = None
    source_note: str | None = None
    signal_focus: str | None = None
    expected_quality: str | None = None

    pain_description: str | None = None
    persona: str | None = None
    scenario: str | None = None
    job_to_be_done: str | None = None
    current_workaround: str | None = None
    frequency_signal: str | None = None
    payment_signal: str | None = None
    confidence: float | None = None
    evidence_quote: str | None = None

    quarantine_id: str | None = None
    quarantine_reason: str | None = None
    quarantine_payload: dict[str, Any] | None = None

    latest_review_label: str | None = None
    latest_review_note: str | None = None
    latest_review_id: str | None = None
    reviewed: bool = False


class ReviewSummary(BaseModel):
    raw_signals: int
    normalized_signals: int
    pain_points: int
    quarantine: int
    reviewed: int
    unreviewed: int
    labels: dict[str, int] = Field(default_factory=dict)


def load_review_items(
    raw_path: str | Path = "data/raw/raw_signals.jsonl",
    normalized_path: str | Path = "data/processed/normalized_signals.jsonl",
    pain_points_path: str | Path = "data/processed/pain_points.jsonl",
    quarantine_path: str | Path = "data/quarantine/invalid_outputs.jsonl",
    reviews_path: str | Path = "data/processed/calibration_reviews.jsonl",
) -> list[ReviewItem]:
    raw_signals = load_raw_signals(raw_path)
    normalized_signals = load_normalized_signals(normalized_path)
    pain_points = load_pain_points(pain_points_path)
    quarantine_records = load_quarantine(quarantine_path)
    reviews = load_reviews(reviews_path)

    raw_by_id = {signal.raw_signal_id: signal for signal in raw_signals}
    normalized_by_raw_id = {signal.raw_signal_id: signal for signal in normalized_signals}
    normalized_by_id = {signal.normalized_signal_id: signal for signal in normalized_signals}
    items: list[ReviewItem] = []
    covered_raw_ids: set[str] = set()

    for pain_point in pain_points:
        raw_signal = raw_by_id.get(pain_point.raw_signal_id)
        normalized_signal = normalized_by_id.get(pain_point.normalized_signal_id)
        item = _item_from_pain_point(pain_point, raw_signal, normalized_signal)
        items.append(_attach_latest_review(item, reviews))
        covered_raw_ids.add(pain_point.raw_signal_id)

    for record in quarantine_records:
        item = _item_from_quarantine(record, raw_by_id, normalized_by_raw_id, normalized_by_id)
        items.append(_attach_latest_review(item, reviews))
        covered_raw_ids.add(item.raw_signal_id)

    for raw_signal in raw_signals:
        if raw_signal.raw_signal_id in covered_raw_ids:
            continue
        normalized_signal = normalized_by_raw_id.get(raw_signal.raw_signal_id)
        item = _item_from_raw(raw_signal, normalized_signal)
        items.append(_attach_latest_review(item, reviews))

    return items


def get_review_summary(
    items: list[ReviewItem],
    raw_path: str | Path = "data/raw/raw_signals.jsonl",
    normalized_path: str | Path = "data/processed/normalized_signals.jsonl",
    pain_points_path: str | Path = "data/processed/pain_points.jsonl",
    quarantine_path: str | Path = "data/quarantine/invalid_outputs.jsonl",
) -> ReviewSummary:
    counts = Counter(item.latest_review_label for item in items if item.latest_review_label)
    labels = {label: counts[label] for label in sorted(VALID_REVIEW_LABELS)}
    reviewed = sum(1 for item in items if item.reviewed)
    return ReviewSummary(
        raw_signals=len(load_raw_signals(raw_path)),
        normalized_signals=len(load_normalized_signals(normalized_path)),
        pain_points=len(load_pain_points(pain_points_path)),
        quarantine=len(load_quarantine(quarantine_path)),
        reviewed=reviewed,
        unreviewed=len(items) - reviewed,
        labels=labels,
    )


def add_review(
    item: ReviewItem,
    label: str,
    reviewer_note: str,
    reviews_path: str | Path = "data/processed/calibration_reviews.jsonl",
    expected_persona: str | None = None,
    expected_evidence_quote: str | None = None,
    expected_pain_description: str | None = None,
    should_be_quarantined: bool | None = None,
) -> CalibrationReview:
    return append_review(
        raw_signal_id=item.raw_signal_id,
        normalized_signal_id=item.normalized_signal_id,
        pain_point_id=item.pain_point_id,
        label=label,
        reviewer_note=reviewer_note,
        expected_persona=expected_persona or None,
        expected_evidence_quote=expected_evidence_quote or None,
        expected_pain_description=expected_pain_description or None,
        should_be_quarantined=should_be_quarantined,
        path=reviews_path,
    )


def get_available_batches(items: list[ReviewItem]) -> list[str]:
    return sorted({item.batch_id or "default" for item in items})


def filter_items_by_batch(items: list[ReviewItem], batch_id: str) -> list[ReviewItem]:
    if batch_id == "All":
        return items
    return [item for item in items if (item.batch_id or "default") == batch_id]


def evidence_quote_found(item: ReviewItem) -> bool:
    quote = (item.evidence_quote or "").strip()
    text = item.normalized_text or ""
    return bool(quote) and quote.lower() in text.lower()


def _item_from_pain_point(
    pain_point: PainPoint,
    raw_signal: RawSignal | None,
    normalized_signal: NormalizedSignal | None,
) -> ReviewItem:
    return ReviewItem(
        raw_signal_id=pain_point.raw_signal_id,
        normalized_signal_id=pain_point.normalized_signal_id,
        pain_point_id=pain_point.pain_point_id,
        item_type="pain_point",
        title=_title(raw_signal, normalized_signal, pain_point.scenario),
        raw_text=raw_signal.raw_text if raw_signal else None,
        normalized_text=normalized_signal.normalized_text if normalized_signal else None,
        source_name=raw_signal.source_name if raw_signal else normalized_signal.source_name if normalized_signal else None,
        source_type=raw_signal.source_type if raw_signal else None,
        url=raw_signal.url if raw_signal else normalized_signal.url if normalized_signal else None,
        language=raw_signal.language if raw_signal else normalized_signal.language if normalized_signal else None,
        domain_tags=raw_signal.domain_tags if raw_signal else normalized_signal.domain_tags if normalized_signal else [],
        batch_id=_first_value(pain_point.batch_id, raw_signal.batch_id if raw_signal else None, normalized_signal.batch_id if normalized_signal else None),
        source_note=_first_value(raw_signal.source_note if raw_signal else None, normalized_signal.source_note if normalized_signal else None),
        signal_focus=_first_value(pain_point.signal_focus, raw_signal.signal_focus if raw_signal else None, normalized_signal.signal_focus if normalized_signal else None),
        expected_quality=_first_value(pain_point.expected_quality, raw_signal.expected_quality if raw_signal else None, normalized_signal.expected_quality if normalized_signal else None),
        pain_description=pain_point.pain_description,
        persona=pain_point.persona,
        scenario=pain_point.scenario,
        job_to_be_done=pain_point.job_to_be_done,
        current_workaround=pain_point.current_workaround,
        frequency_signal=pain_point.frequency_signal,
        payment_signal=pain_point.payment_signal,
        confidence=pain_point.confidence,
        evidence_quote=pain_point.evidence_quote,
    )


def _item_from_quarantine(
    record: QuarantineRecord,
    raw_by_id: dict[str, RawSignal],
    normalized_by_raw_id: dict[str, NormalizedSignal],
    normalized_by_id: dict[str, NormalizedSignal],
) -> ReviewItem:
    payload = record.raw_payload
    raw_id = _payload_raw_id(record, payload)
    normalized_id = _payload_normalized_id(record, payload)
    raw_signal = raw_by_id.get(raw_id or "")
    normalized_signal = normalized_by_id.get(normalized_id or "") or normalized_by_raw_id.get(raw_id or "")
    candidate = payload.get("candidate") if isinstance(payload.get("candidate"), dict) else {}
    raw_signal_id = raw_id or (normalized_signal.raw_signal_id if normalized_signal else record.item_id or record.quarantine_id)
    batch_id = _first_value(
        str(candidate.get("batch_id") or "") or None,
        raw_signal.batch_id if raw_signal else None,
        normalized_signal.batch_id if normalized_signal else None,
        _payload_batch_id(payload),
    )

    return ReviewItem(
        raw_signal_id=raw_signal_id,
        normalized_signal_id=normalized_signal.normalized_signal_id if normalized_signal else normalized_id,
        pain_point_id=str(candidate.get("pain_point_id") or "") or None,
        item_type="quarantine",
        title=_title(raw_signal, normalized_signal, str(candidate.get("scenario") or "")),
        raw_text=raw_signal.raw_text if raw_signal else None,
        normalized_text=normalized_signal.normalized_text if normalized_signal else _payload_text(payload),
        source_name=raw_signal.source_name if raw_signal else normalized_signal.source_name if normalized_signal else None,
        source_type=raw_signal.source_type if raw_signal else None,
        url=raw_signal.url if raw_signal else normalized_signal.url if normalized_signal else None,
        language=raw_signal.language if raw_signal else normalized_signal.language if normalized_signal else None,
        domain_tags=raw_signal.domain_tags if raw_signal else normalized_signal.domain_tags if normalized_signal else [],
        batch_id=batch_id,
        source_note=_first_value(raw_signal.source_note if raw_signal else None, normalized_signal.source_note if normalized_signal else None, _payload_source_note(payload)),
        signal_focus=_first_value(str(candidate.get("signal_focus") or "") or None, raw_signal.signal_focus if raw_signal else None, normalized_signal.signal_focus if normalized_signal else None, _payload_signal_focus(payload)),
        expected_quality=_first_value(str(candidate.get("expected_quality") or "") or None, raw_signal.expected_quality if raw_signal else None, normalized_signal.expected_quality if normalized_signal else None, _payload_expected_quality(payload)),
        pain_description=str(candidate.get("pain_description") or "") or None,
        persona=str(candidate.get("persona") or "") or None,
        scenario=str(candidate.get("scenario") or "") or None,
        job_to_be_done=str(candidate.get("job_to_be_done") or "") or None,
        current_workaround=str(candidate.get("current_workaround") or "") or None,
        frequency_signal=str(candidate.get("frequency_signal") or "") or None,
        payment_signal=str(candidate.get("payment_signal") or "") or None,
        confidence=_optional_float(candidate.get("confidence")),
        evidence_quote=str(candidate.get("evidence_quote") or "") or None,
        quarantine_id=record.quarantine_id,
        quarantine_reason=record.reason,
        quarantine_payload=payload,
    )


def _item_from_raw(raw_signal: RawSignal, normalized_signal: NormalizedSignal | None) -> ReviewItem:
    return ReviewItem(
        raw_signal_id=raw_signal.raw_signal_id,
        normalized_signal_id=normalized_signal.normalized_signal_id if normalized_signal else None,
        item_type="raw_only",
        title=raw_signal.title,
        raw_text=raw_signal.raw_text,
        normalized_text=normalized_signal.normalized_text if normalized_signal else None,
        source_name=raw_signal.source_name,
        source_type=raw_signal.source_type,
        url=raw_signal.url,
        language=raw_signal.language,
        domain_tags=raw_signal.domain_tags,
        batch_id=raw_signal.batch_id,
        source_note=raw_signal.source_note,
        signal_focus=raw_signal.signal_focus,
        expected_quality=raw_signal.expected_quality,
    )


def _attach_latest_review(item: ReviewItem, reviews: list[CalibrationReview]) -> ReviewItem:
    latest = get_latest_review_for_item(
        item.raw_signal_id,
        normalized_signal_id=item.normalized_signal_id,
        pain_point_id=item.pain_point_id,
        reviews=reviews,
    )
    if latest is None:
        return item
    payload = item.model_dump()
    payload.update(
        {
            "latest_review_label": latest.label,
            "latest_review_note": latest.reviewer_note,
            "latest_review_id": latest.review_id,
            "reviewed": True,
        }
    )
    return ReviewItem.model_validate(payload)


def _payload_raw_id(record: QuarantineRecord, payload: dict[str, Any]) -> str | None:
    for key in ("raw_signal", "normalized_signal"):
        nested = payload.get(key)
        if isinstance(nested, dict) and nested.get("raw_signal_id"):
            return str(nested["raw_signal_id"])
    candidate = payload.get("candidate")
    if isinstance(candidate, dict) and candidate.get("raw_signal_id"):
        return str(candidate["raw_signal_id"])
    return record.item_id if record.item_type == "raw_signal" else None


def _payload_normalized_id(record: QuarantineRecord, payload: dict[str, Any]) -> str | None:
    nested = payload.get("normalized_signal")
    if isinstance(nested, dict) and nested.get("normalized_signal_id"):
        return str(nested["normalized_signal_id"])
    candidate = payload.get("candidate")
    if isinstance(candidate, dict) and candidate.get("normalized_signal_id"):
        return str(candidate["normalized_signal_id"])
    return record.item_id if record.item_type == "normalized_signal" else None


def _payload_text(payload: dict[str, Any]) -> str | None:
    nested = payload.get("normalized_signal")
    if isinstance(nested, dict):
        return str(nested.get("normalized_text") or "") or None
    return None


def _payload_batch_id(payload: dict[str, Any]) -> str | None:
    return _payload_field(payload, "batch_id")


def _payload_source_note(payload: dict[str, Any]) -> str | None:
    return _payload_field(payload, "source_note")


def _payload_signal_focus(payload: dict[str, Any]) -> str | None:
    return _payload_field(payload, "signal_focus")


def _payload_expected_quality(payload: dict[str, Any]) -> str | None:
    return _payload_field(payload, "expected_quality")


def _payload_field(payload: dict[str, Any], field_name: str) -> str | None:
    for key in ("raw_signal", "normalized_signal"):
        nested = payload.get(key)
        if isinstance(nested, dict) and nested.get(field_name):
            return str(nested[field_name])
    return None


def _optional_float(value: object) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _title(
    raw_signal: RawSignal | None,
    normalized_signal: NormalizedSignal | None,
    fallback: str | None = None,
) -> str:
    if raw_signal:
        return raw_signal.title
    if normalized_signal:
        return normalized_signal.title
    return fallback or "Untitled review item"


def _first_value(*values: str | None) -> str | None:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return None
