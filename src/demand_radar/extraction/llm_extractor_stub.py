"""LLM extractor stub for Stage 1.5 readiness tests.

This class deliberately does not call external APIs. It only defines the shared
interface that a future structured-output LLM extractor must implement.
"""

from __future__ import annotations

from demand_radar.config.schemas import NormalizedSignal
from demand_radar.extraction.base import PainPointCandidate


class LLMExtractorStub:
    extraction_mode = "llm_stub"

    def __init__(self, fixture_candidates: list[PainPointCandidate] | None = None) -> None:
        self.fixture_candidates = fixture_candidates or []

    def extract(
        self,
        signal: NormalizedSignal,
        pain_point_id: str,
        working_context: dict[str, object],
    ) -> list[PainPointCandidate]:
        if not self.fixture_candidates:
            return []
        candidates: list[PainPointCandidate] = []
        for index, candidate in enumerate(self.fixture_candidates):
            payload = dict(candidate)
            payload.setdefault("pain_point_id", _candidate_id(pain_point_id, index))
            payload.setdefault("raw_signal_id", signal.raw_signal_id)
            payload.setdefault("normalized_signal_id", signal.normalized_signal_id)
            payload.setdefault("extraction_mode", self.extraction_mode)
            candidates.append(payload)
        return candidates


def _candidate_id(base_id: str, index: int) -> str:
    if index == 0:
        return base_id
    prefix, number = base_id.rsplit("_", 1)
    return f"{prefix}_{int(number) + index:06d}"
