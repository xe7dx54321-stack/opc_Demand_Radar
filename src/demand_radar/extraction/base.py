"""Extractor interfaces for Stage 1 pain extraction."""

from __future__ import annotations

from typing import Any, Protocol

from demand_radar.config.schemas import NormalizedSignal


PainPointCandidate = dict[str, Any]


class BasePainExtractor(Protocol):
    extraction_mode: str

    def extract(
        self,
        signal: NormalizedSignal,
        pain_point_id: str,
        working_context: dict[str, object],
    ) -> list[PainPointCandidate]:
        """Return PainPoint-shaped candidate payloads."""


PainExtractor = BasePainExtractor
