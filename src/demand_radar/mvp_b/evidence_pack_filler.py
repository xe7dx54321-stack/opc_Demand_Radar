"""MVP-B: Fill evidence pack draft CSV with extracted pain fields."""
from __future__ import annotations
import csv
from pathlib import Path
from demand_radar.real_evidence.real_evidence_validator import TEMPLATE_COLUMNS

_DRAFT_PATH = Path("examples/real_evidence_pack_ai_investment_tracking_draft.csv")
_FILLED_PATH = Path("examples/real_evidence_pack_ai_investment_tracking_filled.csv")


def _evidence_type_from_pain(pain: dict) -> str:
    strength = pain.get("evidence_strength", "")
    commercial = pain.get("commercial_signal_type") or ""
    current_sol = pain.get("current_solution")
    business_impact = pain.get("business_impact")
    time_cost = pain.get("time_cost_signal")

    if strength in ("strong", "medium") and pain.get("pain_description_zh"):
        return "pain_signal"
    if commercial in ("paid_tool", "budget", "existing_vendor", "purchasing_intent"):
        return "paid_signal"
    if current_sol:
        return "workaround_signal"
    if business_impact or time_cost:
        return "business_impact_signal"
    return "pain_signal"


def fill_evidence_pack(
    draft_path: Path | None = None,
    relevance_dicts: list[dict] | None = None,
    pain_dicts: list[dict] | None = None,
    output_path: Path | None = None,
) -> Path:
    draft = draft_path or _DRAFT_PATH
    out = output_path or _FILLED_PATH

    rel_map: dict[str, dict] = {}
    if relevance_dicts:
        for r in relevance_dicts:
            rel_map[r.get("candidate_id", "")] = r

    pain_map: dict[str, dict] = {}
    if pain_dicts:
        for p in pain_dicts:
            pain_map[p.get("candidate_id", "")] = p

    if not draft.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(",".join(TEMPLATE_COLUMNS) + "\n", encoding="utf-8")
        return out

    with open(draft, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=TEMPLATE_COLUMNS)
        writer.writeheader()
        for row in rows:
            cid = row.get("evidence_id", "")
            rel = rel_map.get(cid, {})
            pain = pain_map.get(cid, {})

            rel_decision = rel.get("relevance_decision", "uncertain")
            should_extract = pain.get("should_extract", False)
            evidence_strength = pain.get("evidence_strength", "reject")

            # Determine if excluded from scoring
            exclude = (
                rel_decision == "exclude"
                or not should_extract
                or evidence_strength == "reject"
                or row.get("is_synthetic", "false").lower() == "true"
            )

            # Fill in fields from pain extraction
            if should_extract and evidence_strength != "reject":
                row["persona"] = pain.get("persona") or row.get("persona", "")
                pc = pain.get("persona_confidence")
                if pc is not None:
                    row["persona_confidence"] = str(pc)
                row["workflow_stage"] = pain.get("workflow_stage") or row.get("workflow_stage", "")
                row["pain_type"] = pain.get("pain_type") or row.get("pain_type", "")
                row["evidence_quote"] = pain.get("evidence_quote") or row.get("evidence_quote", "")
                row["current_solution"] = pain.get("current_solution") or row.get("current_solution", "")
                row["paid_alternative"] = pain.get("paid_alternative") or row.get("paid_alternative", "")
                row["business_impact"] = pain.get("business_impact") or row.get("business_impact", "")
                row["time_cost_signal"] = pain.get("time_cost_signal") or row.get("time_cost_signal", "")
                row["budget_signal"] = pain.get("budget_signal") or row.get("budget_signal", "")
                row["commercial_signal_type"] = pain.get("commercial_signal_type") or row.get("commercial_signal_type", "")
                row["evidence_type"] = _evidence_type_from_pain(pain)
                row["collector_note"] = (
                    f"mvp_b_extracted | strength={evidence_strength} | relevance={rel_decision}"
                )

            row["exclude_from_scoring"] = "true" if exclude else "false"

            # Ensure all columns present
            complete_row = {col: row.get(col, "") for col in TEMPLATE_COLUMNS}
            writer.writerow(complete_row)

    return out