"""Extractor interface for Stage 1 pain extraction."""

from __future__ import annotations

from typing import Protocol

from demand_radar.config.schemas import NormalizedSignal


class PainExtractor(Protocol):
    extraction_mode: str

    def extract(
        self,
        signal: NormalizedSignal,
        pain_point_id: str,
        working_context: dict[str, object],
    ) -> dict[str, object]:
        """Return a PainPoint-shaped candidate payload."""
