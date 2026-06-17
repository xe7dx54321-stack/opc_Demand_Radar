"""D4 review store for second-round reviews, isolated from MVP-C."""
from __future__ import annotations

import json
from pathlib import Path

from demand_radar.ui.d4_review_schema import D4PainSignalReview

DEFAULT_D4_REVIEW_PATH = Path("data/processed/reviews/d4_pain_signal_reviews.jsonl")


class D4ReviewStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or DEFAULT_D4_REVIEW_PATH

    @property
    def path(self) -> Path:
        return self._path

    def _load_raw(self) -> list[dict]:
        if not self._path.exists():
            return []
        out: list[dict] = []
        for line in self._path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out

    def load_reviews(self) -> list[D4PainSignalReview]:
        return [D4PainSignalReview(**data) for data in self._load_raw()]

    def upsert_review(self, review: D4PainSignalReview) -> None:
        """Replace an existing review for the same pain_item_id, or append."""
        existing = self._load_raw()
        found = False
        updated: list[dict] = []
        for row in existing:
            if row.get("pain_item_id") == review.pain_item_id:
                updated.append(review.model_dump(mode="json"))
                found = True
            else:
                updated.append(row)
        if not found:
            updated.append(review.model_dump(mode="json"))

        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            "\n".join(json.dumps(row, ensure_ascii=False) for row in updated) + "\n",
            encoding="utf-8",
        )

    def get_review(self, pain_item_id: str) -> D4PainSignalReview | None:
        for row in self._load_raw():
            if row.get("pain_item_id") == pain_item_id:
                return D4PainSignalReview(**row)
        return None

    def get_reviewed_ids(self) -> set[str]:
        return {
            str(row.get("pain_item_id"))
            for row in self._load_raw()
            if row.get("pain_item_id")
        }

    def summary(self) -> dict[str, int]:
        reviews = self.load_reviews()
        return {
            "total": len(reviews),
            "true_pain": sum(1 for review in reviews if review.true_pain is True),
            "false_pain": sum(1 for review in reviews if review.true_pain is False),
            "uncertain": sum(1 for review in reviews if review.true_pain is None),
            "pursue": sum(1 for review in reviews if review.action_decision == "pursue"),
            "watch": sum(1 for review in reviews if review.action_decision == "watch"),
            "reject": sum(1 for review in reviews if review.action_decision == "reject"),
            "needs_more_evidence": sum(
                1 for review in reviews if review.action_decision == "needs_more_evidence"
            ),
            "commercial_high": sum(
                1 for review in reviews if review.commercial_potential == "high"
            ),
            "commercial_medium": sum(
                1 for review in reviews if review.commercial_potential == "medium"
            ),
            "commercial_low": sum(
                1 for review in reviews if review.commercial_potential == "low"
            ),
            "commercial_unclear": sum(
                1 for review in reviews if review.commercial_potential == "unclear"
            ),
        }
