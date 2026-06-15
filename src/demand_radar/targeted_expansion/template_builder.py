"""Template builder for Stage 3.3 targeted signal collection."""
from __future__ import annotations
import csv
import json
from pathlib import Path
from demand_radar.targeted_expansion.targeted_schema import TargetedSignalTemplateRow
from demand_radar.state.raw_store import utc_now_iso

# Evidence intent allocation ratios
_PAYMENT_INTENTS = {"paid_alternative", "budget_signal"}
_WORKAROUND_INTENTS = {"manual_workaround", "current_solution"}
_IMPACT_INTENTS = {"business_impact", "time_cost"}

_SOURCE_BY_INTENT = {
    "paid_alternative":    "pricing_page",
    "budget_signal":       "product_review",
    "manual_workaround":   "forum_post",
    "current_solution":    "community_discussion",
    "business_impact":     "case_study",
    "time_cost":           "forum_post",
    "product_review":      "product_review",
    "case_study":          "case_study",
}

TEMPLATE_COLUMNS = [
    "target_signal_id", "target_group_id", "target_group_title_zh",
    "target_truth_score_id", "target_current_score", "target_gap_types",
    "evidence_intent", "desired_source_type", "desired_language",
    "suggested_keywords", "title", "raw_text", "url", "source_name",
    "source_type", "published_at", "language", "domain_tags",
    "batch_id", "source_note", "signal_focus", "expected_quality",
    "is_synthetic", "exclude_from_truth_scoring",
    "collection_status", "collector_note",
]


def _allocate_intents(gap_types: list[str], n: int) -> list[str]:
    """Allocate n evidence intents based on gap types."""
    intents: list[str] = []
    payment_gaps = [g for g in gap_types if g in _PAYMENT_INTENTS]
    workaround_gaps = [g for g in gap_types if g in _WORKAROUND_INTENTS]
    impact_gaps = [g for g in gap_types if g in _IMPACT_INTENTS]
    other_gaps = [g for g in gap_types if g not in _PAYMENT_INTENTS | _WORKAROUND_INTENTS | _IMPACT_INTENTS]

    # Proportional allocation
    pay_n = max(round(n * 0.40), 1) if payment_gaps else 0
    wa_n = max(round(n * 0.30), 1) if workaround_gaps else 0
    imp_n = max(round(n * 0.20), 1) if impact_gaps else 0
    other_n = n - pay_n - wa_n - imp_n

    def _repeat(items, count):
        if not items or count <= 0:
            return []
        result = []
        while len(result) < count:
            result.extend(items)
        return result[:count]

    intents.extend(_repeat(payment_gaps or list(_PAYMENT_INTENTS)[:1], pay_n))
    intents.extend(_repeat(workaround_gaps or list(_WORKAROUND_INTENTS)[:1], wa_n))
    intents.extend(_repeat(impact_gaps or list(_IMPACT_INTENTS)[:1], imp_n))
    # Fill remaining
    remaining_types = (payment_gaps + workaround_gaps + impact_gaps + other_gaps) or ["budget_signal"]
    intents.extend(_repeat(remaining_types, max(0, n - len(intents))))
    return intents[:n]


def build_template(
    plans_path: str | Path = "data/processed/targeted_signal_collection_plan.jsonl",
    truth_scores_path: str | Path = "data/processed/truth_scores.jsonl",
    output_path: str | Path = "examples/stage33_targeted_signal_template.csv",
) -> list[TargetedSignalTemplateRow]:
    plans_path = Path(plans_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Load plans
    plans = []
    if plans_path.exists():
        for line in plans_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    plans.append(json.loads(line))
                except Exception:
                    pass

    # Load truth scores for score lookup
    ts_map: dict[str, dict] = {}
    ts_path = Path(truth_scores_path)
    if ts_path.exists():
        for line in ts_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    ts = json.loads(line)
                    ts_map[ts.get("source_group_id", "")] = ts
                except Exception:
                    pass

    rows: list[TargetedSignalTemplateRow] = []
    counter = 1

    for plan in plans:
        n = int(plan.get("target_new_signals", 5))
        gap_types = plan.get("search_keywords_zh", [])  # use as proxy for gap types
        # Get actual gap types from gap_analysis_id via truth_score
        group_id = plan.get("source_group_id", "")
        ts = ts_map.get(group_id, {})
        ts_id = ts.get("truth_score_id", plan.get("truth_score_id", ""))
        current_score = ts.get("truth_score", plan.get("target_current_score"))

        # Gap types: derive from plan keys
        plan_gap_types = []
        for key in ["paid_alternative", "budget_signal", "manual_workaround",
                    "current_solution", "business_impact", "time_cost"]:
            plan_gap_types.append(key)

        intents = _allocate_intents(plan_gap_types, n)
        kw_zh = plan.get("search_keywords_zh", [])
        kw_en = plan.get("search_keywords_en", [])
        all_kw = kw_zh + kw_en

        for i, intent in enumerate(intents):
            sig_id = f"tsig_{counter:06d}"
            counter += 1
            kw_for_row = all_kw[i % len(all_kw)] if all_kw else ""
            row = TargetedSignalTemplateRow(
                target_signal_id=sig_id,
                target_group_id=group_id,
                target_group_title_zh=plan.get("group_title_zh", ""),
                target_truth_score_id=ts_id or None,
                target_current_score=float(current_score) if current_score is not None else None,
                target_gap_types=plan_gap_types[:4],
                evidence_intent=intent,
                desired_source_type=_SOURCE_BY_INTENT.get(intent, "forum_post"),
                desired_language="zh",
                suggested_keywords=[kw_for_row] if kw_for_row else [],
                batch_id="batch_stage33_targeted",
                is_synthetic=False,
                exclude_from_truth_scoring=False,
                collection_status="pending",
            )
            rows.append(row)

    # Write CSV
    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=TEMPLATE_COLUMNS)
        writer.writeheader()
        for row in rows:
            d = row.model_dump()
            d["target_gap_types"] = "|".join(d.get("target_gap_types", []))
            d["suggested_keywords"] = "|".join(d.get("suggested_keywords", []))
            d["domain_tags"] = "|".join(d.get("domain_tags", []))
            writer.writerow(d)

    return rows
