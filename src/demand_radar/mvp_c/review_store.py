"""MVP-C: Review store for pain signal calibration."""
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path

from demand_radar.mvp_b.pain_extraction_schema import ExtractedPainItem
from demand_radar.mvp_c.review_schema import PainSignalReview, PainSignalReviewSummary

_DEFAULT_PATH = Path("data/processed/mvp_c/pain_signal_reviews.jsonl")


class PainSignalReviewStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _DEFAULT_PATH

    def _load_raw(self) -> list[dict]:
        if not self._path.exists():
            return []
        out = []
        for line in self._path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    out.append(json.loads(line))
                except Exception:
                    pass
        return out

    def load_reviews(self) -> list[PainSignalReview]:
        return [PainSignalReview(**d) for d in self._load_raw()]

    def save_review(self, review: PainSignalReview) -> None:
        """Append review (no dedup — use upsert_review for idempotency)."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as f:
            f.write(review.model_dump_json() + "\n")

    def upsert_review(self, review: PainSignalReview) -> None:
        """Replace existing review for same pain_item_id, or append."""
        existing = self._load_raw()
        found = False
        updated: list[dict] = []
        for r in existing:
            if r.get("pain_item_id") == review.pain_item_id:
                updated.append(json.loads(review.model_dump_json()))
                found = True
            else:
                updated.append(r)
        if not found:
            updated.append(json.loads(review.model_dump_json()))
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in updated) + "\n",
            encoding="utf-8",
        )

    def get_review_by_pain_item_id(self, pain_item_id: str) -> PainSignalReview | None:
        for d in self._load_raw():
            if d.get("pain_item_id") == pain_item_id:
                return PainSignalReview(**d)
        return None

    def build_summary(self, pain_items: list[ExtractedPainItem]) -> PainSignalReviewSummary:
        extracted = [p for p in pain_items if p.should_extract]
        reviews = {r.pain_item_id: r for r in self.load_reviews()}

        reviewed = sum(1 for p in extracted if p.pain_item_id in reviews)
        unreviewed = len(extracted) - reviewed

        true_pain = sum(1 for r in reviews.values() if r.true_pain is True)
        false_pain = sum(1 for r in reviews.values() if r.true_pain is False)
        true_pain_unclear = sum(1 for r in reviews.values() if r.true_pain is None and r.review_id)

        commercial_counts = Counter(
            r.commercial_potential for r in reviews.values() if r.commercial_potential
        )
        action_counts = Counter(
            r.action_decision for r in reviews.values() if r.action_decision
        )
        extraction_counts = Counter(
            r.extraction_quality for r in reviews.values() if r.extraction_quality
        )
        error_counter: Counter = Counter()
        for r in reviews.values():
            error_counter.update(r.error_labels)

        return PainSignalReviewSummary(
            total_pain_items=len(extracted),
            reviewed_count=reviewed,
            unreviewed_count=unreviewed,
            true_pain_count=true_pain,
            false_pain_count=false_pain,
            true_pain_unclear_count=true_pain_unclear,
            commercial_high_count=commercial_counts.get("high", 0),
            commercial_medium_count=commercial_counts.get("medium", 0),
            commercial_low_count=commercial_counts.get("low", 0),
            commercial_unclear_count=commercial_counts.get("unclear", 0),
            pursue_count=action_counts.get("pursue", 0),
            watch_count=action_counts.get("watch", 0),
            reject_count=action_counts.get("reject", 0),
            needs_more_evidence_count=action_counts.get("needs_more_evidence", 0),
            extraction_good_count=extraction_counts.get("good", 0),
            extraction_partial_count=extraction_counts.get("partial", 0),
            extraction_bad_count=extraction_counts.get("bad", 0),
            top_error_labels=dict(error_counter.most_common(10)),
        )
