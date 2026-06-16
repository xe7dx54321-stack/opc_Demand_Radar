"""MVP-D summary report generation."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from demand_radar.mvp_d.seed_schema import MVPDRunSummary
from demand_radar.state.raw_store import utc_now_iso


def build_mvp_d_summary_report(
    summary: MVPDRunSummary,
    report_path: Path = Path("outputs/mvp_d/mvp_d_summary_report.md"),
    metadata: dict[str, Any] | None = None,
) -> Path:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    meta = metadata or {}
    lines = [
        "# MVP-D Seeded Evidence Expansion Summary",
        "",
        "## Run Metadata",
        f"- generated_at: {summary.generated_at}",
        f"- radar_commit: {meta.get('radar_commit', 'unknown')}",
        f"- foundation_commit: {meta.get('foundation_commit', 'unknown')}",
        f"- provider: {meta.get('provider', 'none')}",
        f"- model: {meta.get('model', 'none')}",
        f"- real_llm_run: {str(meta.get('real_llm_run', False)).lower()}",
        f"- cache_enabled: {str(meta.get('cache_enabled', True)).lower()}",
        "",
        "## Seed Summary",
        f"- total_reviews: {summary.total_reviews}",
        f"- eligible_seeds: {summary.eligible_seeds}",
        f"- optional_seeds: {summary.optional_seeds}",
        f"- excluded_reviews: {summary.excluded_reviews}",
        f"- selected_seed_ids: {json.dumps(meta.get('selected_seed_ids', []), ensure_ascii=False)}",
        "",
        "## Query Plan",
        f"- total_queries: {meta.get('total_queries', 0)}",
        f"- queries_by_seed: {json.dumps(meta.get('queries_by_seed', {}), ensure_ascii=False)}",
        f"- queries_by_connector: {json.dumps(meta.get('queries_by_connector', {}), ensure_ascii=False)}",
        f"- query_examples: {json.dumps(meta.get('query_examples', []), ensure_ascii=False)}",
        "",
        "## Acquisition Results",
        f"- raw_new_signals: {summary.raw_new_signals}",
        f"- unique_new_signals: {summary.unique_new_signals}",
        f"- deduped_against_existing: {summary.deduped_against_existing}",
        f"- allowed_by_real_signal_gate: {summary.allowed_by_gate}",
        f"- blocked_by_real_signal_gate: {summary.blocked_by_gate}",
        f"- source_url_present: {meta.get('source_url_present', 0)}",
        "",
        "## Extraction Results",
        f"- selected_for_llm: {summary.selected_for_llm}",
        f"- should_extract_true: {summary.should_extract_true}",
        f"- strong: {meta.get('strong', 0)}",
        f"- medium: {meta.get('medium', 0)}",
        f"- weak: {meta.get('weak', 0)}",
        f"- reject: {summary.expansion_pain_items - summary.should_extract_true}",
        f"- failures: {meta.get('failures', 0)}",
        f"- cache_hits: {meta.get('cache_hits', 0)}",
        "",
        "## Evidence Consolidation",
        f"- seeds_with_new_support: {meta.get('seeds_with_new_support', 0)}",
        f"- seeds_without_new_support: {meta.get('seeds_without_new_support', 0)}",
        f"- pursue_candidate: {meta.get('pursue_candidate', 0)}",
        f"- watch: {meta.get('watch', 0)}",
        f"- needs_more_evidence: {meta.get('needs_more_evidence', 0)}",
        f"- reject: {meta.get('reject', 0)}",
        "",
        "## Demand Themes",
        f"- theme_count: {summary.themes}",
        f"- top_themes: {json.dumps(meta.get('top_themes', []), ensure_ascii=False)}",
        "",
        "## Acceptance",
        f"- engineering_acceptance: {summary.engineering_acceptance}",
        f"- product_acceptance: {summary.product_acceptance}",
        f"- can_enter_second_review: {str(summary.can_enter_second_review).lower()}",
        f"- can_enter_product_discovery: {str(summary.can_enter_product_discovery).lower()}",
        f"- reason: {summary.reason}",
        "",
    ]
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return report_path


def build_mvp_d_llm_expansion_pass_report(
    extraction_summary: dict[str, Any] | None = None,
    pain_items: list[dict[str, Any]] | None = None,
    candidates: list[dict[str, Any]] | None = None,
    report_path: Path = Path("outputs/mvp_d/mvp_d_llm_expansion_pass_report.md"),
    seed_profiles_path: Path = Path("data/processed/mvp_d/seed_profiles.jsonl"),
    consolidation_path: Path = Path("data/processed/mvp_d/seed_evidence_consolidation.jsonl"),
) -> Path:
    summary = extraction_summary or {}
    pain_items = pain_items if pain_items is not None else _read_jsonl(Path("data/processed/mvp_d/expansion_pain_items.jsonl"))
    candidates = candidates if candidates is not None else _read_jsonl(Path("data/processed/mvp_d/expansion_evidence_candidates.jsonl"))
    seeds = _read_jsonl(seed_profiles_path)
    consolidations = _read_jsonl(consolidation_path)

    candidate_by_id = {row.get("candidate_id"): row for row in candidates}
    pain_by_seed: dict[str, list[dict[str, Any]]] = {}
    for item in pain_items:
        meta = item.get("metadata") or {}
        cid = item.get("candidate_id")
        seed_id = meta.get("seed_id") or (candidate_by_id.get(cid, {}).get("metadata") or {}).get("seed_id")
        if seed_id:
            pain_by_seed.setdefault(str(seed_id), []).append(item)

    consolidation_by_seed = {row.get("seed_id"): row for row in consolidations}
    seed_map = {row.get("seed_id"): row for row in seeds}

    provider = str(summary.get("provider", "none"))
    model = str(summary.get("model", "none"))
    real_llm_run = bool(summary.get("real_llm_run", False))
    cache_enabled = bool(summary.get("cache_enabled", False))
    prompt_version = str(summary.get("prompt_version", "n/a"))
    run_scope = str(summary.get("run_scope", "n/a"))

    should_extract_items = [item for item in pain_items if item.get("should_extract")]
    failures = [item for item in pain_items if "failed" in str(item.get("reject_reason", "")).lower()]
    strong = sum(1 for item in pain_items if item.get("evidence_strength") == "strong")
    medium = sum(1 for item in pain_items if item.get("evidence_strength") == "medium")
    weak = sum(1 for item in pain_items if item.get("evidence_strength") == "weak")
    reject = sum(1 for item in pain_items if not item.get("should_extract"))
    cache_hits = sum(1 for item in pain_items if (item.get("metadata") or {}).get("cache_hit"))
    quote_present = sum(1 for item in should_extract_items if item.get("evidence_quote"))
    quote_matched = sum(1 for item in should_extract_items if (item.get("metadata") or {}).get("quote_matched"))
    persona_populated = sum(1 for item in should_extract_items if item.get("persona"))
    workflow_populated = sum(1 for item in should_extract_items if item.get("workflow_stage"))
    pain_type_populated = sum(1 for item in should_extract_items if item.get("pain_type"))
    commercial_signal_count = sum(
        1
        for item in should_extract_items
        if item.get("commercial_signal_type") or item.get("budget_signal") or item.get("paid_alternative")
    )

    seed_rows = []
    for seed_id, seed in seed_map.items():
        seed_pains = pain_by_seed.get(seed_id, [])
        strong_n = sum(1 for item in seed_pains if item.get("evidence_strength") == "strong")
        medium_n = sum(1 for item in seed_pains if item.get("evidence_strength") == "medium")
        weak_n = sum(1 for item in seed_pains if item.get("evidence_strength") == "weak")
        consolidation = consolidation_by_seed.get(seed_id, {})
        recommendation = consolidation.get("recommendation") or _seed_recommendation(seed, seed_pains)
        original_pain = seed.get("pain_description_zh") or seed.get("title") or "n/a"
        seed_rows.append(
            {
                "seed_id": seed_id,
                "original_pain": original_pain,
                "new_extracted_pain": len(seed_pains),
                "strong": strong_n,
                "medium": medium_n,
                "weak": weak_n,
                "recommendation": recommendation,
                "commercial_potential": seed.get("commercial_potential", "unclear"),
            }
        )

    selected_for_llm = int(summary.get("selected_for_llm", len(candidates)))
    processed = int(summary.get("processed", len(pain_items)))
    should_extract_true = int(summary.get("should_extract_true", len(should_extract_items)))
    blocked_reason = summary.get("blocked_reason")
    status = str(summary.get("status", "completed"))
    engineering_acceptance, product_acceptance, can_enter_second_review, can_enter_product_discovery, reason = _expansion_acceptance(
        summary,
        seed_rows,
    )

    lines = [
        "# MVP-D LLM Expansion Pass Report",
        "",
        "## Run Metadata",
        f"- generated_at: {summary.get('generated_at', utc_now_iso())}",
        f"- radar_commit: {summary.get('radar_commit', 'unknown')}",
        f"- foundation_commit: {summary.get('foundation_commit', 'unknown')}",
        f"- provider: {provider}",
        f"- model: {model}",
        f"- real_llm_run: {str(real_llm_run).lower()}",
        f"- cache_enabled: {str(cache_enabled).lower()}",
        f"- prompt_version: {prompt_version}",
        f"- run_scope: {run_scope}",
        f"- status: {status}",
        f"- blocked_reason: {blocked_reason or 'n/a'}",
        "",
        "## Input",
        f"- gate_allowed_candidates: {int(summary.get('allowed_by_gate', len(candidates)))}",
        f"- selected_for_llm: {selected_for_llm}",
        f"- by_seed: {json.dumps({seed_id: len(items) for seed_id, items in pain_by_seed.items()}, ensure_ascii=False)}",
        f"- by_source: {json.dumps(_count_by(candidates, 'source_type'), ensure_ascii=False)}",
        "",
        "## LLM Extraction",
        f"- processed: {processed}",
        f"- should_extract_true: {should_extract_true}",
        f"- rejected: {reject}",
        f"- strong: {strong}",
        f"- medium: {medium}",
        f"- weak: {weak}",
        f"- reject: {reject}",
        f"- failures: {len(failures)}",
        f"- cache_hits: {cache_hits}",
        "",
        "## Quality Checks",
        f"- evidence_quote_present: {quote_present}",
        f"- evidence_quote_matched_raw_text: {quote_matched}",
        f"- persona_populated: {persona_populated}",
        f"- workflow_stage_populated: {workflow_populated}",
        f"- pain_type_populated: {pain_type_populated}",
        f"- commercial_signal_count: {commercial_signal_count}",
        "",
        "## Seed Support",
    ]

    if seed_rows:
        for row in seed_rows:
            lines.extend(
                [
                    f"### {row['seed_id']}",
                    f"- original pain: {row['original_pain']}",
                    f"- new_extracted_pain: {row['new_extracted_pain']}",
                    f"- strong: {row['strong']}",
                    f"- medium: {row['medium']}",
                    f"- weak: {row['weak']}",
                    f"- commercial_potential: {row['commercial_potential']}",
                    f"- recommendation: {row['recommendation']}",
                    "",
                ]
            )
    else:
        lines.append("No reviewed seeds found.")

    lines.extend(
        [
            "## Acceptance",
            f"- engineering_acceptance: {engineering_acceptance}",
            f"- product_acceptance: {product_acceptance}",
            f"- can_enter_second_review: {str(can_enter_second_review).lower()}",
            f"- can_enter_product_discovery: {str(can_enter_product_discovery).lower()}",
            f"- reason: {reason}",
            "",
        ]
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return report_path


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _count_by(rows: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        key = str(row.get(field) or "unknown")
        counts[key] = counts.get(key, 0) + 1
    return counts


def _seed_recommendation(seed: dict[str, Any], pains: list[dict[str, Any]]) -> str:
    strong = sum(1 for item in pains if item.get("evidence_strength") == "strong")
    medium = sum(1 for item in pains if item.get("evidence_strength") == "medium")
    source_urls = {item.get("source_url") for item in pains if item.get("source_url")}
    if seed.get("true_pain") is True and len(pains) >= 3 and strong + medium >= 3 and len(source_urls) >= 3:
        return "pursue_candidate"
    if len(pains) >= 1:
        return "watch"
    if seed:
        return "needs_more_evidence"
    return "reject"


def _expansion_acceptance(
    summary: dict[str, Any],
    seed_rows: list[dict[str, Any]],
) -> tuple[str, str, bool, bool, str]:
    status = str(summary.get("status", "completed"))
    if status == "blocked" or not summary.get("real_llm_run"):
        reason = summary.get("blocked_reason") or "real LLM extraction not executed"
        return "blocked", "blocked", False, False, reason

    should_extract_true = int(summary.get("should_extract_true", 0))
    strong = int(summary.get("strong", 0))
    medium = int(summary.get("medium", 0))
    seeds_with_support = sum(1 for row in seed_rows if row["new_extracted_pain"] >= 2)
    supported_themes = sum(1 for row in seed_rows if row["recommendation"] in {"watch", "pursue_candidate"})

    engineering_ok = (
        int(summary.get("selected_for_llm", 0)) > 0
        and summary.get("real_llm_run")
        and provider_not_none(summary)
        and int(summary.get("processed", 0)) > 0
    )
    product_ok = (
        should_extract_true >= 5
        and strong + medium >= 3
        and seeds_with_support >= 2
        and supported_themes >= 1
    )
    if engineering_ok and product_ok:
        return "pass", "pass", True, True, "real LLM expansion pass produced usable new evidence"
    if engineering_ok:
        return "pass", "partial", True, supported_themes >= 1, "real LLM ran but expansion evidence is still limited"
    return "partial", "blocked", False, False, "real LLM extraction did not reach engineering acceptance"


def provider_not_none(summary: dict[str, Any]) -> bool:
    provider = str(summary.get("provider", "none"))
    model = str(summary.get("model", "none"))
    return provider not in {"none", ""} and model not in {"none", ""}
