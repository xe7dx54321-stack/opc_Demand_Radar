"""Lightweight theme grouping for MVP-D evidence themes."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from demand_radar.mvp_d.seed_schema import EvidenceTheme
from demand_radar.state.raw_store import next_ids, utc_now_iso


def build_demand_themes(
    seeds_path: Path,
    consolidations_path: Path,
    output_path: Path,
    report_path: Path,
) -> list[EvidenceTheme]:
    seeds = _read_jsonl(seeds_path)
    consolidations = _read_jsonl(consolidations_path)
    seed_map = {row["seed_id"]: row for row in seeds}

    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in consolidations:
        seed = seed_map.get(row["seed_id"])
        if not seed:
            continue
        key = (
            _group_key(seed.get("persona")),
            _group_key(seed.get("workflow_stage")),
            _group_key(seed.get("pain_type")),
        )
        grouped[key].append({"seed": seed, "consolidation": row})

    theme_ids = next_ids("theme_", [], len(grouped))
    themes: list[EvidenceTheme] = []
    for theme_id, (key, items) in zip(theme_ids, grouped.items(), strict=True):
        themes.append(_build_theme(theme_id, key, items))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "\n".join(theme.model_dump_json() for theme in themes) + ("\n" if themes else ""),
        encoding="utf-8",
    )
    _write_report(themes, report_path)
    return themes


def _build_theme(theme_id: str, key: tuple[str, str, str], items: list[dict[str, Any]]) -> EvidenceTheme:
    persona_group, workflow_group, pain_type_group = key
    seeds = [item["seed"] for item in items]
    consolidations = [item["consolidation"] for item in items]
    reviewed_seed_count = sum(1 for seed in seeds if seed.get("true_pain") is True)
    new_evidence_count = sum(item.get("new_extracted_pain_count", 0) for item in consolidations)
    evidence_count = len(items) + new_evidence_count
    commercial_potential = _best_commercial(seed.get("commercial_potential") for seed in seeds)
    confidence = min(0.95, 0.45 + 0.08 * len(items) + 0.05 * new_evidence_count)
    recommendation = _recommendation(items)
    title = _theme_title(persona_group, workflow_group, pain_type_group)
    summary = _theme_summary(items)
    quotes = [
        seed.get("evidence_quote") or seed.get("title") or seed.get("pain_description_zh") or ""
        for seed in seeds
    ]
    return EvidenceTheme(
        theme_id=theme_id,
        theme_title_zh=title,
        seed_ids=[seed["seed_id"] for seed in seeds],
        pain_item_ids=[seed["pain_item_id"] for seed in seeds],
        evidence_candidate_ids=[],
        persona_group=persona_group or None,
        workflow_group=workflow_group or None,
        pain_type_group=pain_type_group or None,
        theme_summary_zh=summary,
        evidence_count=evidence_count,
        reviewed_seed_count=reviewed_seed_count,
        new_evidence_count=new_evidence_count,
        commercial_potential=commercial_potential,
        confidence=round(confidence, 2),
        action_recommendation=recommendation,
        representative_quotes=[quote for quote in quotes if quote][:5],
        source_urls=[seed.get("source_url") for seed in seeds if seed.get("source_url")][:5],
        created_at=utc_now_iso(),
        metadata={"group_key": [persona_group, workflow_group, pain_type_group]},
    )


def _theme_title(persona_group: str, workflow_group: str, pain_type_group: str) -> str:
    persona_label = persona_group if persona_group != "unknown" else "相关用户"
    workflow_label = workflow_group if workflow_group != "unknown" else "相关工作流"
    pain_label = pain_type_group if pain_type_group != "unknown" else "关键痛点"
    return f"{persona_label} 在 {workflow_label} 中的 {pain_label} 需求"


def _theme_summary(items: list[dict[str, Any]]) -> str:
    texts = []
    for item in items:
        seed = item["seed"]
        consolidation = item["consolidation"]
        if seed.get("pain_description_zh"):
            texts.append(seed["pain_description_zh"])
        reason = consolidation.get("recommendation_reason_zh")
        if reason:
            texts.append(reason)
    deduped = []
    for text in texts:
        if text and text not in deduped:
            deduped.append(text)
    summary = " ".join(deduped)
    return summary[:300] if summary else "该主题来自人工确认 pain seed 的轻量规则归组。"


def _best_commercial(values) -> str:
    order = ["high", "medium", "unclear", "low"]
    present = [value for value in values if value]
    for choice in order:
        if choice in present:
            return choice
    return "unclear"


def _recommendation(items: list[dict[str, Any]]) -> str:
    recs = [item["consolidation"].get("recommendation") for item in items]
    if "pursue_candidate" in recs:
        return "pursue_candidate"
    if "watch" in recs:
        return "watch"
    if "needs_more_evidence" in recs:
        return "needs_more_evidence"
    return "reject"


def _group_key(value: str | None) -> str:
    text = str(value or "").strip().lower()
    return text or "unknown"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_report(themes: list[EvidenceTheme], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# MVP-D Demand Theme Grouping Report",
        "",
        f"- theme_count: {len(themes)}",
        "",
    ]
    for theme in themes:
        lines.extend(
            [
                f"## {theme.theme_title_zh}",
                f"- theme_id: {theme.theme_id}",
                f"- persona_group: {theme.persona_group or 'n/a'}",
                f"- workflow_group: {theme.workflow_group or 'n/a'}",
                f"- pain_type_group: {theme.pain_type_group or 'n/a'}",
                f"- evidence_count: {theme.evidence_count}",
                f"- reviewed_seed_count: {theme.reviewed_seed_count}",
                f"- new_evidence_count: {theme.new_evidence_count}",
                f"- commercial_potential: {theme.commercial_potential}",
                f"- confidence: {theme.confidence}",
                f"- action_recommendation: {theme.action_recommendation}",
                f"- seed_ids: {', '.join(theme.seed_ids)}",
                f"- source_urls: {'; '.join(theme.source_urls) if theme.source_urls else 'n/a'}",
                "",
                theme.theme_summary_zh,
                "",
            ]
        )
    if not themes:
        lines.append("No themes generated.")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
