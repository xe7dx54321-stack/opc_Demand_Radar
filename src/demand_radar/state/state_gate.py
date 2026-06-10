"""State gates for promoting candidate outputs into Working State."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from demand_radar.config.schemas import PainPoint


@dataclass(frozen=True, slots=True)
class GateResult:
    passed: bool
    reason: str | None = None


def pain_point_gate(
    candidate: PainPoint | dict[str, Any],
    normalized_text: str,
    min_confidence: float = 0.65,
) -> GateResult:
    payload = candidate.model_dump(mode="json") if isinstance(candidate, PainPoint) else candidate
    pain_description = str(payload.get("pain_description") or "").strip()
    evidence_quote = str(payload.get("evidence_quote") or "").strip()
    confidence = payload.get("confidence")

    if not evidence_quote:
        return GateResult(False, "missing_evidence_quote")
    if evidence_quote.lower() not in normalized_text.lower():
        return GateResult(False, "evidence_quote_not_found")
    try:
        confidence_float = float(confidence)
    except (TypeError, ValueError):
        return GateResult(False, "schema_invalid")
    if confidence_float < min_confidence:
        return GateResult(False, "low_confidence")
    if not pain_description:
        return GateResult(False, "schema_invalid")

    try:
        if not isinstance(candidate, PainPoint):
            PainPoint.model_validate(payload)
    except ValidationError:
        return GateResult(False, "schema_invalid")
    return GateResult(True)
