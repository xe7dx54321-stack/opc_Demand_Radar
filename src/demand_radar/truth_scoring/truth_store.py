"""Store layer for Truth Scoring: read/write truth_scores and reviews."""
from __future__ import annotations

import json
from pathlib import Path

from demand_radar.truth_scoring.truth_schema import TruthScore, TruthScoreReview

TRUTH_SCORES_PATH = Path("data/processed/truth_scores.jsonl")
TRUTH_REVIEWS_PATH = Path("data/processed/truth_score_reviews.jsonl")


def write_truth_scores(
    scores: list[TruthScore],
    path: str | Path = TRUTH_SCORES_PATH,
) -> int:
    """Overwrite the truth scores file with the given scores. Returns count written."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [score.model_dump_json() for score in scores]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return len(scores)


def load_truth_scores(path: str | Path = TRUTH_SCORES_PATH) -> list[TruthScore]:
    """Load all TruthScore records. Returns empty list if file missing or empty."""
    path = Path(path)
    if not path.exists():
        return []
    scores = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            scores.append(TruthScore.model_validate_json(line))
        except Exception:
            continue
    return scores


def append_truth_score_review(
    review: TruthScoreReview,
    path: str | Path = TRUTH_REVIEWS_PATH,
) -> None:
    """Append a single review record to the reviews file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(review.model_dump_json() + "\n")


def load_truth_score_reviews(path: str | Path = TRUTH_REVIEWS_PATH) -> list[TruthScoreReview]:
    """Load all review records. Returns empty list if file missing."""
    path = Path(path)
    if not path.exists():
        return []
    reviews = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            reviews.append(TruthScoreReview.model_validate_json(line))
        except Exception:
            continue
    return reviews


def get_latest_review(
    truth_score_id: str,
    path: str | Path = TRUTH_REVIEWS_PATH,
) -> TruthScoreReview | None:
    """Return the latest review for a given truth_score_id (last in file)."""
    reviews = load_truth_score_reviews(path)
    matches = [r for r in reviews if r.truth_score_id == truth_score_id]
    return matches[-1] if matches else None
