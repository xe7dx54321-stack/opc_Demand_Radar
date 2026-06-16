"""MVP-D: Select reviewed pain signals as expansion seeds."""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from demand_radar.mvp_d.seed_schema import ReviewedPainSeed
from demand_radar.state.raw_store import next_ids, utc_now_iso

_CONFIG_PATH = Path("configs/seeded_expansion_config.yaml")
_BLOCK_URLS = {"example.com", "example.org", "example.net"}
_BLOCK_TITLES = {"example domain", "placeholder", "synthetic", "inherited sample", "manual seed"}


def _load_cfg(p: Path | None = None) -> dict:
    cfg_path = p or _CONFIG_PATH
    with open(cfg_path, encoding="utf-8") as f:
        return yaml.safe_load(f).get("seeded_expansion", {})


def _is_blocked_url(url: str | None) -> bool:
    if not url:
        return True
    ul = url.lower()
    return any(b in ul for b in _BLOCK_URLS)


def _is_blocked_title(title: str | None) -> bool:
    if not title:
        return False
    tl = title.lower()
    return any(b in tl for b in _BLOCK_TITLES)


@dataclass
class SeedSelectionSummary:
    total_reviews: int = 0
    eligible_seeds: int = 0
    optional_seeds: int = 0
    excluded_reviews: int = 0
    excluded_reasons: dict = field(default_factory=dict)
    selected_seed_ids: list[str] = field(default_factory=list)


def select_seeds(
    config_path: Path | None = None,
    pain_items_path: Path | None = None,
    reviews_path: Path | None = None,
    output_path: Path | None = None,
    report_path: Path | None = Path("outputs/mvp_d/seed_selection_report.md"),
    max_seeds_override: int | None = None,
) -> tuple[list[ReviewedPainSeed], SeedSelectionSummary]:
    cfg = _load_cfg(config_path)
    sel_cfg = cfg.get("seed_selection", {})
    max_seeds = int(sel_cfg.get("max_seeds", 5) if max_seeds_override is None else max_seeds_override)
    allowed_actions = set(sel_cfg.get("allowed_actions", ["needs_more_evidence", "watch"]))
    min_evidence_quality = set(sel_cfg.get("min_evidence_quality", ["medium", "strong"]))
    include_true_pain = bool(sel_cfg.get("include_true_pain", True))
    include_uncertain = bool(sel_cfg.get("include_uncertain_pain", False))

    pi_path = pain_items_path or Path(cfg.get("input", {}).get("extracted_pain_items_path", "data/processed/mvp_b/extracted_pain_items.jsonl"))
    rev_path = reviews_path or Path(cfg.get("input", {}).get("reviews_path", "data/processed/mvp_c/pain_signal_reviews.jsonl"))
    out_path = output_path or Path(cfg.get("output", {}).get("seed_profiles_path", "data/processed/mvp_d/seed_profiles.jsonl"))

    pain_items: dict[str, dict] = {}
    if pi_path.exists():
        for line in pi_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                d = json.loads(line)
                pain_items[d.get("pain_item_id", "")] = d

    reviews: list[dict] = []
    if rev_path.exists():
        for line in rev_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                reviews.append(json.loads(line))

    summary = SeedSelectionSummary(total_reviews=len(reviews))
    seeds: list[ReviewedPainSeed] = []
    seed_ids = next_ids("seed_", [], max_seeds + 10)
    idx = 0

    for rev in reviews:
        pain_item_id = rev.get("pain_item_id", "")
        pain = pain_items.get(pain_item_id, {})
        true_pain = rev.get("true_pain")
        action = rev.get("action_decision", "")
        evidence_q = rev.get("evidence_quality", "")
        commercial = rev.get("commercial_potential", "unclear")
        source_url = pain.get("source_url", "")

        # Gate checks
        if _is_blocked_url(source_url):
            summary.excluded_reviews += 1
            summary.excluded_reasons["blocked_url"] = summary.excluded_reasons.get("blocked_url", 0) + 1
            continue
        if _is_blocked_title(pain.get("title")):
            summary.excluded_reviews += 1
            summary.excluded_reasons["blocked_title"] = summary.excluded_reasons.get("blocked_title", 0) + 1
            continue
        if true_pain is False:
            summary.excluded_reviews += 1
            summary.excluded_reasons["false_pain"] = summary.excluded_reasons.get("false_pain", 0) + 1
            continue

        # Main seed criteria
        is_main = (
            true_pain is True
            and action in allowed_actions
            and evidence_q in min_evidence_quality
        )
        # Optional seed: uncertain pain but good evidence
        is_optional = (
            include_uncertain
            and true_pain is None
            and action in allowed_actions
            and evidence_q in {"medium", "strong"}
        )

        if not is_main and not is_optional:
            summary.excluded_reviews += 1
            summary.excluded_reasons["quality_threshold"] = summary.excluded_reasons.get("quality_threshold", 0) + 1
            continue

        if idx >= max_seeds:
            break

        # Priority scoring
        if true_pain is True and commercial in {"high"} and evidence_q == "strong":
            priority = "high"
        elif true_pain is True and evidence_q in {"medium", "strong"}:
            priority = "medium"
        else:
            priority = "low"

        reason_parts = []
        if true_pain is True:
            reason_parts.append("true_pain confirmed")
        if commercial in {"high", "medium"}:
            reason_parts.append(f"commercial={commercial}")
        if evidence_q in {"strong", "medium"}:
            reason_parts.append(f"evidence={evidence_q}")
        reason_parts.append(f"action={action}")

        seed = ReviewedPainSeed(
            seed_id=seed_ids[idx],
            pain_item_id=pain_item_id,
            candidate_id=rev.get("candidate_id", ""),
            title=pain.get("title"),
            source_url=source_url,
            source_type=pain.get("source_type"),
            persona=pain.get("persona"),
            workflow_stage=pain.get("workflow_stage"),
            pain_type=pain.get("pain_type"),
            pain_description_zh=pain.get("pain_description_zh"),
            evidence_quote=pain.get("evidence_quote"),
            true_pain=bool(true_pain) if true_pain is not None else False,
            commercial_potential=commercial,
            evidence_quality=evidence_q,
            action_decision=action,
            expansion_priority=priority,
            seed_reason_zh=" / ".join(reason_parts),
            created_at=utc_now_iso(),
        )
        seeds.append(seed)
        if is_optional:
            summary.optional_seeds += 1
        else:
            summary.eligible_seeds += 1
        summary.selected_seed_ids.append(seed.seed_id)
        idx += 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for s in seeds:
            f.write(s.model_dump_json() + "\n")

    if report_path is not None:
        build_seed_selection_report(seeds, summary, report_path)

    return seeds, summary


def build_seed_selection_report(
    seeds: list[ReviewedPainSeed],
    summary: SeedSelectionSummary,
    output_path: Path = Path("outputs/mvp_d/seed_selection_report.md"),
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# MVP-D Seed Selection Report",
        "",
        "## Summary",
        f"- total_reviews: {summary.total_reviews}",
        f"- eligible_seeds: {summary.eligible_seeds}",
        f"- optional_seeds: {summary.optional_seeds}",
        f"- excluded_reviews: {summary.excluded_reviews}",
        f"- excluded_reasons: {json.dumps(summary.excluded_reasons, ensure_ascii=False)}",
        f"- selected_seed_ids: {json.dumps(summary.selected_seed_ids, ensure_ascii=False)}",
        "",
        "## Selected Seeds",
        "",
    ]
    if not seeds:
        lines.append("No reviewed pain seeds eligible for expansion.")
    for seed in seeds:
        lines.extend(
            [
                f"### {seed.seed_id}",
                f"- pain_item_id: {seed.pain_item_id}",
                f"- candidate_id: {seed.candidate_id}",
                f"- title: {seed.title or 'n/a'}",
                f"- source_url: {seed.source_url}",
                f"- persona: {seed.persona or 'n/a'}",
                f"- workflow_stage: {seed.workflow_stage or 'n/a'}",
                f"- pain_type: {seed.pain_type or 'n/a'}",
                f"- commercial_potential: {seed.commercial_potential or 'n/a'}",
                f"- evidence_quality: {seed.evidence_quality or 'n/a'}",
                f"- action_decision: {seed.action_decision or 'n/a'}",
                f"- expansion_priority: {seed.expansion_priority}",
                f"- seed_reason_zh: {seed.seed_reason_zh}",
                "",
            ]
        )
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return output_path
