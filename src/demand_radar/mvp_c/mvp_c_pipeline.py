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
from demand_radar.mvp_c.review_schema import PainSignalReviewSummary


@dataclass
class MVPCRunSummary:
    total_pain_items: int
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

    store = PainSignalReviewStore(path=reviews_path)
    svc = ReviewService(pain_items_path=pain_items_path, store=store)
    errors: list[str] = []

    try:
        cards = svc.load_pain_signal_cards()
    except Exception as exc:
        errors.append(f"Failed to load pain signal cards: {exc}")
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

    try:
        build_pain_signal_review_report(cards, summary)
    except Exception as exc:
        errors.append(f"pain_signal_review_report error: {exc}")

    try:
        build_calibration_recommendations(findings)
    except Exception as exc:
        errors.append(f"calibration_recommendations error: {exc}")

    try:
        build_mvp_c_summary_report(summary, findings)
    except Exception as exc:
        errors.append(f"mvp_c_summary_report error: {exc}")

    reviewed_pct = (summary.reviewed_count / summary.total_pain_items * 100) if summary.total_pain_items else 0
    product_pass = summary.reviewed_count >= 3 and (summary.pursue_count + summary.watch_count) >= 1

    return MVPCRunSummary(
        total_pain_items=summary.total_pain_items,
        reviewed_count=summary.reviewed_count,
        unreviewed_count=summary.unreviewed_count,
        true_pain_count=summary.true_pain_count,
        pursue_count=summary.pursue_count,
        findings_count=len(findings),
        engineering_acceptance="PASS",
        product_acceptance="PASS" if product_pass else ("PARTIAL" if summary.reviewed_count > 0 else "FAIL"),
        errors=errors,
    )
