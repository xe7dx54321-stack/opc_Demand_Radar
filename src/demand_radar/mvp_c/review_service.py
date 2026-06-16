"""MVP-C: Review service - loads pain items + reviews for UI."""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from demand_radar.mvp_c.review_schema import PainSignalReview, PainSignalReviewSummary
from demand_radar.mvp_c.review_store import PainSignalReviewStore

_PAIN_ITEMS_PATH = Path("data/processed/mvp_b/extracted_pain_items.jsonl")


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


@dataclass
class PainSignalCard:
    pain_item_id: str
    candidate_id: str
    title: str | None
    source_url: str | None
    source_type: str | None
    persona: str | None
    workflow_stage: str | None
    pain_type: str | None
    pain_description_zh: str | None
    evidence_quote: str | None
    current_solution: str | None
    commercial_signal_type: str | None
    evidence_strength: str
    confidence: float
    reasoning_summary_zh: str | None
    existing_review: PainSignalReview | None = None


class ReviewService:
    def __init__(
        self,
        pain_items_path: Path | None = None,
        store: PainSignalReviewStore | None = None,
    ) -> None:
        self._pain_path = pain_items_path or _PAIN_ITEMS_PATH
        self._store = store or PainSignalReviewStore()

    def load_pain_signal_cards(
        self,
        only_extracted: bool = True,
        filter_strength: str | None = None,
        filter_action: str | None = None,
        reviewed_only: bool | None = None,
    ) -> list[PainSignalCard]:
        items = _load_jsonl(self._pain_path)
        if only_extracted:
            items = [p for p in items if p.get("should_extract")]

        reviews = {r.pain_item_id: r for r in self._store.load_reviews()}
        cards: list[PainSignalCard] = []
        for p in items:
            pid = p.get("pain_item_id", "")
            rev = reviews.get(pid)

            if reviewed_only is True and rev is None:
                continue
            if reviewed_only is False and rev is not None:
                continue
            if filter_strength and p.get("evidence_strength") != filter_strength:
                continue
            if filter_action and (rev is None or rev.action_decision != filter_action):
                continue

            cards.append(PainSignalCard(
                pain_item_id=pid,
                candidate_id=p.get("candidate_id", ""),
                title=p.get("title"),
                source_url=p.get("source_url"),
                source_type=p.get("source_type"),
                persona=p.get("persona"),
                workflow_stage=p.get("workflow_stage"),
                pain_type=p.get("pain_type"),
                pain_description_zh=p.get("pain_description_zh"),
                evidence_quote=p.get("evidence_quote"),
                current_solution=p.get("current_solution"),
                commercial_signal_type=p.get("commercial_signal_type"),
                evidence_strength=p.get("evidence_strength", "unknown"),
                confidence=float(p.get("confidence", 0.0)),
                reasoning_summary_zh=p.get("reasoning_summary_zh"),
                existing_review=rev,
            ))
        return cards

    def save_review(self, review: PainSignalReview) -> None:
        self._store.upsert_review(review)

    def get_summary(self) -> PainSignalReviewSummary:
        from demand_radar.mvp_b.pain_extraction_schema import ExtractedPainItem
        raw_items = _load_jsonl(self._pain_path)
        pain_items = []
        for d in raw_items:
            try:
                pain_items.append(ExtractedPainItem(**d))
            except Exception:
                pass
        return self._store.build_summary(pain_items)
