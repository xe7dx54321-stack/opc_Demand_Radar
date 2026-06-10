"""Lightweight similarity scoring for Stage 2 demand clustering."""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from demand_radar.config.schemas import PainPoint


DEFAULT_WEIGHTS = {
    "pain_description_weight": 0.45,
    "job_to_be_done_weight": 0.25,
    "current_workaround_weight": 0.15,
    "persona_weight": 0.10,
    "domain_weight": 0.05,
}


@dataclass(frozen=True)
class SimilarityBreakdown:
    pain_description: float
    job_to_be_done: float
    current_workaround: float
    persona: float
    domain: float
    total: float


def pain_point_similarity(
    left: PainPoint,
    right: PainPoint,
    weights: dict[str, float] | None = None,
) -> SimilarityBreakdown:
    """Return a weighted 0-100 similarity score for two pain points."""

    active_weights = {**DEFAULT_WEIGHTS, **(weights or {})}
    pain = text_similarity(left.pain_description, right.pain_description)
    job = text_similarity(left.job_to_be_done or "", right.job_to_be_done or "")
    workaround = text_similarity(left.current_workaround or "", right.current_workaround or "")
    persona = exact_or_empty_similarity(left.persona, right.persona)
    domain = overlap_similarity(_domain_tokens(left), _domain_tokens(right))
    total = (
        pain * active_weights["pain_description_weight"]
        + job * active_weights["job_to_be_done_weight"]
        + workaround * active_weights["current_workaround_weight"]
        + persona * active_weights["persona_weight"]
        + domain * active_weights["domain_weight"]
    )
    return SimilarityBreakdown(
        pain_description=round(pain, 2),
        job_to_be_done=round(job, 2),
        current_workaround=round(workaround, 2),
        persona=round(persona, 2),
        domain=round(domain, 2),
        total=round(total, 2),
    )


def text_similarity(left: str, right: str) -> float:
    left_norm = _normalize_text(left)
    right_norm = _normalize_text(right)
    if not left_norm or not right_norm:
        return 0.0
    sequence_score = SequenceMatcher(None, left_norm, right_norm).ratio() * 100
    token_score = overlap_similarity(set(left_norm.split()), set(right_norm.split()))
    return max(sequence_score, token_score)


def exact_or_empty_similarity(left: str | None, right: str | None) -> float:
    left_norm = _normalize_text(left or "")
    right_norm = _normalize_text(right or "")
    if not left_norm or not right_norm:
        return 50.0
    return 100.0 if left_norm == right_norm else 0.0


def overlap_similarity(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    intersection = len(left & right)
    union = len(left | right)
    return 100.0 * intersection / union if union else 0.0


def _domain_tokens(pain_point: PainPoint) -> set[str]:
    # Stage 1 PainPoint does not carry domain tags, so infer coarse workflow
    # tokens from task-like fields.
    blob = " ".join(
        [
            pain_point.persona or "",
            pain_point.scenario or "",
            pain_point.job_to_be_done or "",
            pain_point.current_workaround or "",
            pain_point.pain_description,
        ]
    )
    return set(_normalize_text(blob).split())


def _normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[_\-/]+", " ", text)
    text = re.sub(r"[^\w\u4e00-\u9fff]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text
