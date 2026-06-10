"""Processed Working State JSONL helpers."""

from __future__ import annotations

from pathlib import Path

from demand_radar.config.schemas import NormalizedSignal, PainPoint
from demand_radar.state.raw_store import read_jsonl, write_jsonl


def load_normalized_signals(
    path: str | Path = "data/processed/normalized_signals.jsonl",
) -> list[NormalizedSignal]:
    return [NormalizedSignal.model_validate(row) for row in read_jsonl(path)]


def write_normalized_signals(
    signals: list[NormalizedSignal],
    path: str | Path = "data/processed/normalized_signals.jsonl",
) -> int:
    return write_jsonl(path, signals)


def load_pain_points(path: str | Path = "data/processed/pain_points.jsonl") -> list[PainPoint]:
    return [PainPoint.model_validate(row) for row in read_jsonl(path)]


def write_pain_points(
    pain_points: list[PainPoint],
    path: str | Path = "data/processed/pain_points.jsonl",
) -> int:
    return write_jsonl(path, pain_points)
