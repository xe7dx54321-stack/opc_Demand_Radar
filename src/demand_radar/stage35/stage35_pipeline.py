"""Stage 3.5 pipeline orchestration."""
from __future__ import annotations
import json
from pathlib import Path
from demand_radar.stage35.stage35_candidate_selector import select_stage35_candidates
from demand_radar.stage35.stage35_template_builder import build_stage35_template
from demand_radar.stage35.stage35_validator import validate_stage35_signals, load_stage35_validations
from demand_radar.stage35.stage35_gate import evaluate_stage4_gate
from demand_radar.stage35.stage35_report import (
    build_stage35_expansion_report, build_stage35_stable_delta_report,
    build_stage35_gate_report,
)
from demand_radar.stage35.stage35_store import (
    load_selected_candidates, write_run_summary, load_run_summary,
)
from demand_radar.stage35.stage35_schema import Stage35RunSummary
from demand_radar.state.raw_store import next_ids, utc_now_iso
from demand_radar.lineage.lineage_propagator import snapshot_truth_state


def ensure_snapshot(name: str = "before_stage35", archive_dir: str = "outputs/archive/before_stage35") -> tuple[str, str]:
    """Ensure a before snapshot exists. Returns (path, quality)."""
    dest = Path(archive_dir)
    if dest.exists() and (dest / "truth_scores.jsonl").exists():
        return str(dest), "full"
    # Create snapshot now
    extra = {
        "stable_truth_score_delta.jsonl": "data/processed/stable_truth_score_delta.jsonl",
        "candidate_lineage.jsonl": "data/processed/candidate_lineage.jsonl",
        "targeted_evidence_attribution.jsonl": "data/processed/targeted_evidence_attribution.jsonl",
    }
    sources = {
        "truth_scores.jsonl": "data/processed/truth_scores.jsonl",
        "calibrated_llm_ai_reviewed_cluster_groups.jsonl": "data/processed/calibrated_llm_ai_reviewed_cluster_groups.jsonl",
        "evidence_gap_analysis.jsonl": "data/processed/evidence_gap_analysis.jsonl",
        "targeted_signal_collection_plan.jsonl": "data/processed/targeted_signal_collection_plan.jsonl",
        **extra,
    }
    result = snapshot_truth_state(name=name, sources=sources, base_dir="outputs/archive")
    quality = "full" if (Path(str(result)) / "truth_scores.jsonl").exists() else "partial"
    return str(result), quality


def run_stage35(
    snapshot_name: str = "before_stage35",
    filled_sample_path: str = "examples/real_signal_samples_stage35.csv",
    base_sample_path: str | None = None,
) -> dict:
    """Main Stage 3.5 pipeline (no LLM)."""
    # 1. Ensure snapshot
    snap_path, snap_quality = ensure_snapshot(name=snapshot_name, archive_dir=f"outputs/archive/{snapshot_name}")
    print(f"  Snapshot: {snap_path} (quality={snap_quality})")

    # 2. Select candidates
    candidates = select_stage35_candidates()
    if not candidates:
        print("  No eligible Stage 3.5 candidates found. Check truth_scores.jsonl.")
        return {"status": "no_candidates"}
    print(f"  Selected {len(candidates)} candidates")

    # 3. Build template
    template_rows = build_stage35_template(total_rows=24)
    print(f"  Template rows: {len(template_rows)}")

    # 4. Validate if filled sample exists
    filled_path = Path(filled_sample_path)
    validations: list[dict] = []
    if filled_path.exists():
        validations = validate_stage35_signals(filled_path)
        print(f"  Validations: {len(validations)}")

    # 5. Combined input (basic stats only; full combine done in run-stage35-full)
    valid_n = sum(1 for v in validations if v.get("status") == "valid")
    warn_n = sum(1 for v in validations if v.get("status") == "warning")
    inv_n = sum(1 for v in validations if v.get("status") == "invalid")

    pay_n = sum(1 for v in validations if v.get("evidence_intent") in ("paid_alternative", "budget_signal") and v.get("include_in_combined_input"))
    wa_n = sum(1 for v in validations if v.get("evidence_intent") in ("manual_workaround", "current_solution") and v.get("include_in_combined_input"))
    imp_n = sum(1 for v in validations if v.get("evidence_intent") in ("business_impact", "time_cost") and v.get("include_in_combined_input"))

    # 6. Gate (based on existing stable deltas)
    stable_deltas: list[dict] = []
    sd_path = Path("data/processed/stable_truth_score_delta.jsonl")
    if sd_path.exists():
        for line in sd_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    stable_deltas.append(json.loads(line))
                except Exception:
                    pass
    gate = evaluate_stage4_gate(stable_deltas, lineage_baseline_quality=snap_quality)

    # 7. Build reports
    cands_dicts = [c.model_dump() for c in candidates]
    summary_dict = {
        "before_snapshot_name": snapshot_name,
        "lineage_baseline_quality": snap_quality,
        "selected_candidates": len(candidates),
        "template_rows": len(template_rows),
        "filled_signals": len(validations),
        "valid_signals": valid_n,
        "warning_signals": warn_n,
        "invalid_signals": inv_n,
        "payment_or_cost_signals": pay_n,
        "workaround_or_current_solution_signals": wa_n,
        "stage4_gate_status": gate.status,
    }
    build_stage35_expansion_report(summary_dict, cands_dicts, validations)
    build_stage35_stable_delta_report(stable_deltas)
    build_stage35_gate_report(gate.model_dump())

    # 8. Persist run summary
    run_id = next_ids("s35run", [], 1)[0]
    run_summary = Stage35RunSummary(
        run_id=run_id,
        before_snapshot_name=snapshot_name,
        before_snapshot_path=snap_path,
        lineage_baseline_quality=snap_quality,
        selected_candidates=len(candidates),
        template_rows=len(template_rows),
        filled_signals=len(validations),
        valid_signals=valid_n,
        warning_signals=warn_n,
        invalid_signals=inv_n,
        excluded_signals=0,
        combined_rows=0,
        payment_or_cost_signals=pay_n,
        workaround_or_current_solution_signals=wa_n,
        business_impact_or_time_cost_signals=imp_n,
        stage4_gate_status=gate.status,
        created_at=utc_now_iso(),
    )
    write_run_summary(run_summary)

    return summary_dict
