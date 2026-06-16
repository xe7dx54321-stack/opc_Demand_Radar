"""MVP-B: Orchestration pipeline."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MVPBRunSummary:
    domain_id: str
    candidates_processed: int
    include_count: int
    uncertain_count: int
    exclude_count: int
    pain_processed: int
    should_extract_count: int
    strong_count: int
    medium_count: int
    r1_before: dict = field(default_factory=dict)
    r1_after: dict = field(default_factory=dict)
    filled_csv: Path | None = None
    errors: list[str] = field(default_factory=list)


_CANDIDATES_PATH = Path("data/processed/acquisition/evidence_candidates.jsonl")
_DRAFT_CSV = Path("examples/real_evidence_pack_ai_investment_tracking_draft.csv")
_RELEVANCE_OUT = Path("data/processed/mvp_b/domain_relevance_scores.jsonl")
_PAIN_OUT = Path("data/processed/mvp_b/extracted_pain_items.jsonl")
_FILLED_CSV = Path("examples/real_evidence_pack_ai_investment_tracking_filled.csv")
_R1_ITEMS_OUT = Path("data/processed/mvp_b/r1_items.jsonl")
_R1_VAL_OUT = Path("data/processed/mvp_b/r1_validation.jsonl")


def run_mvp_b(
    domain_id: str = "ai_investment_tracking",
    use_cached_acquisition: bool = True,
    max_items: int | None = None,
    llm_client=None,
    candidates_path: Path | None = None,
    relevance_output: Path | None = None,
    pain_output: Path | None = None,
    filled_csv_output: Path | None = None,
) -> MVPBRunSummary:
    import json

    from demand_radar.mvp_b.domain_relevance_filter import run_domain_relevance_filter
    from demand_radar.mvp_b.evidence_pack_filler import fill_evidence_pack
    from demand_radar.mvp_b.mvp_b_report import (
        build_domain_relevance_report,
        build_mvp_b_summary_report,
        build_pain_extraction_report,
        build_top_pain_signals_report,
    )
    from demand_radar.mvp_b.mvp_b_store import (
        load_pain_dicts,
        load_relevance_dicts,
        write_pain_items,
        write_relevance_results,
    )
    from demand_radar.mvp_b.pain_extraction_runner import run_pain_extraction

    errors: list[str] = []
    cands_path = candidates_path or _CANDIDATES_PATH

    # Step 1: Load candidates
    def _load_jsonl(p: Path) -> list[dict]:
        if not p.exists():
            return []
        out = []
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    out.append(json.loads(line))
                except Exception:
                    pass
        return out

    candidates = _load_jsonl(cands_path)
    if max_items:
        candidates = candidates[:max_items]

    if not candidates:
        return MVPBRunSummary(
            domain_id=domain_id,
            candidates_processed=0,
            include_count=0,
            uncertain_count=0,
            exclude_count=0,
            pain_processed=0,
            should_extract_count=0,
            strong_count=0,
            medium_count=0,
            errors=["No candidates found"],
        )

    # Step 2: Domain relevance filter
    rel_out = relevance_output or _RELEVANCE_OUT
    rel_results = run_domain_relevance_filter(
        candidates, llm_client=llm_client, output_path=rel_out
    )
    write_relevance_results(rel_results, rel_out)
    rel_dicts = [r.model_dump() for r in rel_results]

    inc = sum(1 for r in rel_dicts if r.get("relevance_decision") == "include")
    unc = sum(1 for r in rel_dicts if r.get("relevance_decision") == "uncertain")
    exc = sum(1 for r in rel_dicts if r.get("relevance_decision") == "exclude")

    # Step 3: Pain extraction
    pain_out = pain_output or _PAIN_OUT
    pain_items = run_pain_extraction(
        candidates, rel_dicts, llm_client=llm_client, max_items=max_items, output_path=pain_out
    )
    write_pain_items(pain_items, pain_out)
    pain_dicts = [it.model_dump() for it in pain_items]

    should_n = sum(1 for p in pain_dicts if p.get("should_extract"))
    strong_n = sum(1 for p in pain_dicts if p.get("evidence_strength") == "strong")
    medium_n = sum(1 for p in pain_dicts if p.get("evidence_strength") == "medium")

    # Step 4: R1 validation before (draft)
    r1_before: dict = {"valid": 0, "warning": 0, "invalid": 0}
    try:
        from demand_radar.real_evidence.real_evidence_validator import validate_real_evidence_pack
        if _DRAFT_CSV.exists():
            items_b, vals_b = validate_real_evidence_pack(_DRAFT_CSV, _R1_ITEMS_OUT, _R1_VAL_OUT)
            r1_before = {
                "valid": sum(1 for v in vals_b if v.status == "valid"),
                "warning": sum(1 for v in vals_b if v.status == "warning"),
                "invalid": sum(1 for v in vals_b if v.status == "invalid"),
            }
    except Exception as exc:
        errors.append(f"R1 before validation error: {exc}")

    # Step 5: Fill evidence pack
    filled = filled_csv_output or _FILLED_CSV
    fill_evidence_pack(
        draft_path=_DRAFT_CSV,
        relevance_dicts=rel_dicts,
        pain_dicts=pain_dicts,
        output_path=filled,
    )

    # Step 6: R1 validation after (filled)
    r1_after: dict = {"valid": 0, "warning": 0, "invalid": 0}
    try:
        from demand_radar.real_evidence.real_evidence_validator import validate_real_evidence_pack
        items_a, vals_a = validate_real_evidence_pack(
            filled,
            Path("data/processed/mvp_b/r1_items_after.jsonl"),
            Path("data/processed/mvp_b/r1_val_after.jsonl"),
        )
        r1_after = {
            "valid": sum(1 for v in vals_a if v.status == "valid"),
            "warning": sum(1 for v in vals_a if v.status == "warning"),
            "invalid": sum(1 for v in vals_a if v.status == "invalid"),
        }
    except Exception as exc:
        errors.append(f"R1 after validation error: {exc}")

    # Step 7: Reports
    build_domain_relevance_report(rel_dicts)
    build_pain_extraction_report(pain_dicts)
    build_top_pain_signals_report(pain_dicts)
    build_mvp_b_summary_report(rel_dicts, pain_dicts, r1_before, r1_after)

    return MVPBRunSummary(
        domain_id=domain_id,
        candidates_processed=len(candidates),
        include_count=inc,
        uncertain_count=unc,
        exclude_count=exc,
        pain_processed=len(pain_items),
        should_extract_count=should_n,
        strong_count=strong_n,
        medium_count=medium_n,
        r1_before=r1_before,
        r1_after=r1_after,
        filled_csv=filled,
        errors=errors,
    )