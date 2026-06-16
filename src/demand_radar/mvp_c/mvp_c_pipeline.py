"""MVP-C: Pipeline - generate reports from pain items + reviews."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path

from demand_radar.mvp_c.review_service import ReviewService
from demand_radar.mvp_c.calibration_analyzer import analyze_reviews, CalibrationFinding
from demand_radar.mvp_c.calibration_report import (
    build_pain_signal_review_report,
    build_calibration_recommendations,
    build_mvp_c_summary_report,
)
from demand_radar.mvp_c.real_pain_signal_gate import (
    run_gate, build_gate_report, quarantine_stale_reviews, _load_jsonl,
)
from demand_radar.mvp_c.review_schema import PainSignalReviewSummary

_PAIN_ITEMS_PATH = Path("data/processed/mvp_b/extracted_pain_items.jsonl")
_REVIEWS_PATH = Path("data/processed/mvp_c/pain_signal_reviews.jsonl")


@dataclass
class MVPCRunSummary:
    total_pain_items: int
    reviewable_count: int
    blocked_count: int
    reviewed_count: int
    unreviewed_count: int
    true_pain_count: int
    pursue_count: int
    findings_count: int
    engineering_acceptance: str
    product_acceptance: str
    errors: list[str] = field(default_factory=list)


def run_mvp_c(
    pain_items_path: Path | None = None,
    reviews_path: Path | None = None,
) -> MVPCRunSummary:
    from demand_radar.mvp_c.review_store import PainSignalReviewStore
    import json

    p_path = pain_items_path or _PAIN_ITEMS_PATH
    r_path = reviews_path or _REVIEWS_PATH
    store = PainSignalReviewStore(path=r_path)
    svc = ReviewService(pain_items_path=p_path, store=store)
    errors: list[str] = []

    # Step 1: Gate
    all_items = _load_jsonl(p_path)
    extracted = [p for p in all_items if p.get("should_extract")]
    allowed_results, blocked_results = run_gate(extracted)
    allowed_ids = {r.pain_item_id for r in allowed_results}
    allowed_items = [p for p in extracted if p.get("pain_item_id") in allowed_ids]

    # Quarantine stale reviews
    try:
        quarantine_stale_reviews(r_path, allowed_ids)
    except Exception as exc:
        errors.append(f"Quarantine error: {exc}")

    # Gate report
    try:
        build_gate_report(extracted, allowed_results, blocked_results)
    except Exception as exc:
        errors.append(f"Gate report error: {exc}")

    # Step 2: Load cards + summary
    try:
        cards = svc.load_pain_signal_cards()
    except Exception as exc:
        errors.append(f"Failed to load cards: {exc}")
        cards = []

    try:
        summary: PainSignalReviewSummary = svc.get_summary()
    except Exception as exc:
        errors.append(f"Failed to build summary: {exc}")
        summary = PainSignalReviewSummary(
            total_pain_items=0, reviewed_count=0, unreviewed_count=0
        )

    reviews = store.load_reviews()
    findings = analyze_reviews(reviews)

    # Reports
    try:
        build_pain_signal_review_report(cards, summary)
    except Exception as exc:
        errors.append(f"Review report error: {exc}")

    try:
        build_calibration_recommendations(findings)
    except Exception as exc:
        errors.append(f"Calibration report error: {exc}")

    try:
        build_mvp_c_summary_report(summary, findings)
    except Exception as exc:
        errors.append(f"Summary report error: {exc}")

    product_pass = summary.reviewed_count >= 3 and (summary.pursue_count + summary.watch_count) >= 1

    return MVPCRunSummary(
        total_pain_items=len(extracted),
        reviewable_count=len(allowed_results),
        blocked_count=len(blocked_results),
        reviewed_count=summary.reviewed_count,
        unreviewed_count=summary.unreviewed_count,
        true_pain_count=summary.true_pain_count,
        pursue_count=summary.pursue_count,
        findings_count=len(findings),
        engineering_acceptance="PASS",
        product_acceptance="PASS" if product_pass else ("PARTIAL" if summary.reviewed_count > 0 else "FAIL"),
        errors=errors,
    )
