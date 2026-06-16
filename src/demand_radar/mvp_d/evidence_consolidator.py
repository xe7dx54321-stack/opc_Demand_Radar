"""MVP-D evidence consolidation for reviewed seeds."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from demand_radar.mvp_d.seed_schema import SeedConsolidation
from demand_radar.state.raw_store import next_ids, utc_now_iso


_CONFIG_PATH = Path("configs/seeded_expansion_config.yaml")


def _load_cfg(path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or _CONFIG_PATH
    with cfg_path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle).get("seeded_expansion", {})


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def consolidate_evidence(
    config_path: Path | None = None,
    seeds_path: Path | None = None,
    candidates_path: Path | None = None,
    pain_items_path: Path | None = None,
    output_path: Path | None = None,
    report_path: Path = Path("outputs/mvp_d/seed_evidence_consolidation_report.md"),
) -> list[SeedConsolidation]:
    cfg = _load_cfg(config_path)
    output_cfg = cfg.get("output", {})
    seed_rows = _read_jsonl(
        seeds_path or Path(output_cfg.get("seed_profiles_path", "data/processed/mvp_d/seed_profiles.jsonl"))
    )
    candidate_rows = _read_jsonl(
        candidates_path
        or Path(
            output_cfg.get(
                "expansion_evidence_candidates_path",
                "data/processed/mvp_d/expansion_evidence_candidates.jsonl",
            )
        )
    )
    pain_rows = _read_jsonl(
        pain_items_path
        or Path(output_cfg.get("expansion_pain_items_path", "data/processed/mvp_d/expansion_pain_items.jsonl"))
    )
    out_path = output_path or Path(
        output_cfg.get("seed_consolidation_path", "data/processed/mvp_d/seed_evidence_consolidation.jsonl")
    )
    candidate_by_id = {row.get("candidate_id"): row for row in candidate_rows}
    ids = next_ids("seed_consolidation_", [], len(seed_rows))
    consolidations: list[SeedConsolidation] = []

    for index, seed in enumerate(seed_rows):
        seed_id = seed.get("seed_id", "")
        seed_candidates = [row for row in candidate_rows if (row.get("metadata") or {}).get("seed_id") == seed_id]
        seed_pains = [
            row
            for row in pain_rows
            if (candidate_by_id.get(row.get("candidate_id"), {}).get("metadata") or {}).get("seed_id")
            == seed_id
            and row.get("should_extract")
        ]
        strengths = [row.get("evidence_strength") for row in seed_pains]
        source_urls = {row.get("source_url") for row in seed_pains if row.get("source_url")}
        commercial_signal_count = sum(
            1
            for row in seed_pains
            if row.get("commercial_signal_type") or row.get("budget_signal") or row.get("paid_alternative")
        )
        strong_medium = strengths.count("strong") + strengths.count("medium")
        recommendation, reason = _recommendation(seed, seed_candidates, seed_pains, strong_medium, source_urls)
        consolidations.append(
            SeedConsolidation(
                consolidation_id=ids[index],
                seed_id=seed_id,
                pain_item_id=seed.get("pain_item_id", ""),
                original_title=seed.get("title"),
                new_related_candidates_count=len(seed_candidates),
                new_extracted_pain_count=len(seed_pains),
                strong_evidence_count=strengths.count("strong"),
                medium_evidence_count=strengths.count("medium"),
                weak_evidence_count=strengths.count("weak"),
                commercial_signal_count=commercial_signal_count,
                source_url_count=len(source_urls),
                recommendation=recommendation,
                recommendation_reason_zh=reason,
                created_at=utc_now_iso(),
                metadata={
                    "source_urls": sorted(source_urls),
                    "commercial_potential": seed.get("commercial_potential"),
                    "evidence_quality": seed.get("evidence_quality"),
                },
            )
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        "\n".join(item.model_dump_json() for item in consolidations) + ("\n" if consolidations else ""),
        encoding="utf-8",
    )
    _write_report(consolidations, report_path)
    return consolidations


def _recommendation(
    seed: dict[str, Any],
    seed_candidates: list[dict[str, Any]],
    seed_pains: list[dict[str, Any]],
    strong_medium: int,
    source_urls: set[str],
) -> tuple[str, str]:
    if (
        seed.get("true_pain") is True
        and seed.get("commercial_potential") in {"high", "medium"}
        and len(seed_pains) >= 3
        and strong_medium >= 3
        and len(source_urls) >= 3
    ):
        return "pursue_candidate", "新增证据数量、强度和来源数均达到追踪候选门槛。"
    if len(seed_pains) >= 1:
        return "watch", "已有新增支持证据，但数量或强度还不足以进入追踪候选。"
    if seed_candidates:
        return "needs_more_evidence", "找到了相关候选，但尚未抽取出足够痛点证据。"
    return "reject", "未找到支持该 seed 的新增证据。"


def _write_report(items: list[SeedConsolidation], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# MVP-D Seed Evidence Consolidation Report", ""]
    for item in items:
        lines.extend(
            [
                f"## {item.seed_id}",
                f"- original_pain_item_id: {item.pain_item_id}",
                f"- original_title: {item.original_title or 'n/a'}",
                f"- new_related_candidates_count: {item.new_related_candidates_count}",
                f"- new_extracted_pain_count: {item.new_extracted_pain_count}",
                f"- strong_evidence_count: {item.strong_evidence_count}",
                f"- medium_evidence_count: {item.medium_evidence_count}",
                f"- weak_evidence_count: {item.weak_evidence_count}",
                f"- commercial_signal_count: {item.commercial_signal_count}",
                f"- source_url_count: {item.source_url_count}",
                f"- recommendation: {item.recommendation}",
                f"- reason: {item.recommendation_reason_zh}",
                "",
            ]
        )
    if not items:
        lines.append("No seed consolidation rows generated.")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
