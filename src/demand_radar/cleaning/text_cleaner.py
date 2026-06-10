"""Cleaning and normalization for Stage 1."""

from __future__ import annotations

import html
import re
from pathlib import Path

from demand_radar.config.load_config import load_yaml
from demand_radar.config.schemas import NormalizedSignal
from demand_radar.state.processed_store import write_normalized_signals
from demand_radar.state.quarantine_store import append_quarantine
from demand_radar.state.raw_store import load_raw_signals


TAG_RE = re.compile(r"<[^>]+>")
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
CODE_BLOCK_RE = re.compile(r"```.*?```", re.DOTALL)
WHITESPACE_RE = re.compile(r"\s+")


def clean_text(text: str, max_chars: int | None = None) -> str:
    text = html.unescape(text or "")
    text = CODE_BLOCK_RE.sub(" ", text)
    text = TAG_RE.sub(" ", text)
    text = MARKDOWN_LINK_RE.sub(r"\1", text)
    text = text.replace("#", " ")
    text = WHITESPACE_RE.sub(" ", text).strip()
    if max_chars is not None and max_chars > 0:
        return text[:max_chars]
    return text


def normalize_signals(
    raw_path: str | Path = "data/raw/raw_signals.jsonl",
    output_path: str | Path = "data/processed/normalized_signals.jsonl",
    quarantine_path: str | Path = "data/quarantine/invalid_outputs.jsonl",
    extraction_config_path: str | Path = "configs/extraction_config.yaml",
) -> list[NormalizedSignal]:
    config = load_yaml(extraction_config_path)
    max_chars = int(config.get("pain_extraction", {}).get("max_text_chars", 8000))
    normalized: list[NormalizedSignal] = []

    for index, raw_signal in enumerate(load_raw_signals(raw_path), start=1):
        normalized_text = clean_text(raw_signal.raw_text, max_chars=max_chars)
        if not normalized_text:
            append_quarantine(
                "normalized_signal",
                "empty_text",
                raw_signal.model_dump(mode="json"),
                item_id=raw_signal.raw_signal_id,
                path=quarantine_path,
            )
            continue
        signal = NormalizedSignal(
            raw_signal_id=raw_signal.raw_signal_id,
            normalized_signal_id=f"norm_{index:06d}",
            source_name=raw_signal.source_name,
            title=raw_signal.title,
            normalized_text=normalized_text,
            url=raw_signal.url,
            language=raw_signal.language,
            domain_tags=raw_signal.domain_tags,
            batch_id=raw_signal.batch_id,
            source_note=raw_signal.source_note,
            signal_focus=raw_signal.signal_focus,
            expected_quality=raw_signal.expected_quality,
            content_hash=raw_signal.content_hash,
        )
        normalized.append(signal)

    write_normalized_signals(normalized, output_path)
    return normalized
