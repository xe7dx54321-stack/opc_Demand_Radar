"""Stage 1 Pain Extraction Loop."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError

from demand_radar.config.load_config import load_yaml
from demand_radar.config.schemas import NormalizedSignal, PainPoint
from demand_radar.extraction.base import BasePainExtractor, PainPointCandidate
from demand_radar.extraction.llm_extractor_stub import LLMExtractorStub
from demand_radar.extraction.rule_based_extractor import RuleBasedPainExtractor
from demand_radar.state.processed_store import load_normalized_signals, write_pain_points
from demand_radar.state.quarantine_store import append_quarantine
from demand_radar.state.state_gate import pain_point_gate


def run_pain_extraction(
    normalized_path: str | Path = "data/processed/normalized_signals.jsonl",
    output_path: str | Path = "data/processed/pain_points.jsonl",
    quarantine_path: str | Path = "data/quarantine/invalid_outputs.jsonl",
    domain_config_path: str | Path = "configs/domain_config.yaml",
    extraction_config_path: str | Path = "configs/extraction_config.yaml",
) -> list[PainPoint]:
    domain_config = load_yaml(domain_config_path)
    extraction_config = load_yaml(extraction_config_path)
    min_confidence = float(extraction_config.get("pain_extraction", {}).get("min_confidence", 0.65))
    mode = str(extraction_config.get("pain_extraction", {}).get("default_mode", "rule_based"))
    extractor = _build_extractor(mode)
    normalized_signals = load_normalized_signals(normalized_path)
    accepted: list[PainPoint] = []
    next_pain_number = 1

    for signal in normalized_signals:
        pain_point_id = _pain_point_id(next_pain_number)
        working_context = build_working_context(signal, domain_config, extraction_config)
        try:
            candidates = _as_candidate_list(extractor.extract(signal, pain_point_id, working_context))
        except Exception as exc:  # pragma: no cover - defensive boundary
            append_quarantine(
                "pain_point",
                "extractor_error",
                {"normalized_signal": signal.model_dump(mode="json"), "error": str(exc)},
                item_id=signal.normalized_signal_id,
                path=quarantine_path,
            )
            continue

        if not candidates:
            append_quarantine(
                "pain_point",
                "missing_evidence_quote",
                {"candidate": {}, "normalized_signal": signal.model_dump(mode="json")},
                item_id=signal.normalized_signal_id,
                path=quarantine_path,
            )
            continue

        for candidate in candidates:
            candidate = dict(candidate)
            candidate["pain_point_id"] = _pain_point_id(next_pain_number)
            candidate["batch_id"] = signal.batch_id
            candidate["signal_focus"] = signal.signal_focus
            candidate["expected_quality"] = signal.expected_quality
            next_pain_number += 1
            gate = pain_point_gate(candidate, signal.normalized_text, min_confidence=min_confidence)
            if not gate.passed:
                append_quarantine(
                    "pain_point",
                    gate.reason or "schema_invalid",
                    {"candidate": candidate, "normalized_signal": signal.model_dump(mode="json")},
                    item_id=str(candidate.get("pain_point_id") or signal.normalized_signal_id),
                    path=quarantine_path,
                )
                continue

            try:
                accepted.append(PainPoint.model_validate(candidate))
            except ValidationError as exc:
                append_quarantine(
                    "pain_point",
                    "schema_invalid",
                    {"candidate": candidate, "errors": exc.errors(), "normalized_signal": signal.model_dump(mode="json")},
                    item_id=str(candidate.get("pain_point_id") or signal.normalized_signal_id),
                    path=quarantine_path,
                )

    write_pain_points(accepted, output_path)
    return accepted


def build_working_context(
    signal: NormalizedSignal,
    domain_config: dict[str, Any],
    extraction_config: dict[str, Any],
) -> dict[str, Any]:
    return {
        "normalized_signal": signal.model_dump(mode="json"),
        "domain_config": {
            "domains": domain_config.get("domains", []),
            "personas": domain_config.get("personas", []),
            "exclude": domain_config.get("exclude", []),
            "signal_types": domain_config.get("signal_types", []),
        },
        "extraction_config": extraction_config.get("pain_extraction", {}),
        "pain_schema": {
            "required": ["pain_description", "evidence_quote", "confidence", "extraction_mode"],
            "rules": [
                "pain_description must be non-empty",
                "evidence_quote must be copied from normalized_text",
                "confidence must be between 0 and 1",
            ],
        },
    }


def _as_candidate_list(result: object) -> list[PainPointCandidate]:
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        return [result]
    return []


def _pain_point_id(number: int) -> str:
    return f"pain_{number:06d}"


def _build_extractor(mode: str) -> BasePainExtractor:
    if mode == "rule_based":
        return RuleBasedPainExtractor()
    if mode in {"llm", "llm_stub"}:
        return LLMExtractorStub()
    raise ValueError(f"Unsupported pain extraction mode: {mode}")
