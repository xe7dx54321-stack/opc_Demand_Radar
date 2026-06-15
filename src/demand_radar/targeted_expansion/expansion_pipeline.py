"""Stage 3.3 expansion pipeline."""
from __future__ import annotations
from pathlib import Path
from demand_radar.targeted_expansion.template_builder import build_template
from demand_radar.targeted_expansion.targeted_validator import validate_targeted_signals,load_validations
from demand_radar.targeted_expansion.combined_input_builder import build_combined_input
from demand_radar.targeted_expansion.expansion_report import build_targeted_expansion_report,build_truth_score_delta_report
from demand_radar.targeted_expansion.expansion_store import write_expansion_summary
from demand_radar.targeted_expansion.targeted_schema import TargetedExpansionSummary
from demand_radar.state.raw_store import utc_now_iso
def run_stage33(targeted_path=None,validate=True,combine=True):
    rows=build_template()
    template_rows=len(rows)
    validations=[]
    filled=0
    if validate and targeted_path and Path(targeted_path).exists():
        validations=validate_targeted_signals(targeted_path)
        filled=sum(1 for v in validations if v.status!='warning' or True)
    combined_rows=0
    base_rows=0
    targeted_included=0
    dupes=0
    if combine and targeted_path and Path(targeted_path).exists():
        result=build_combined_input(targeted_path=targeted_path)
        combined_rows=result.get('combined_rows',0)
        base_rows=result.get('base_rows',0)
        targeted_included=result.get('targeted_rows_included',0)
        dupes=result.get('duplicates_removed',0)
    valid_n=sum(1 for v in validations if v.status=='valid')
    warn_n=sum(1 for v in validations if v.status=='warning')
    inv_n=sum(1 for v in validations if v.status=='invalid')
    exc_n=sum(1 for v in validations if v.status=='excluded')
    summary=TargetedExpansionSummary(template_rows=template_rows,filled_signals=filled,valid_signals=valid_n,warning_signals=warn_n,invalid_signals=inv_n,excluded_synthetic=exc_n,combined_input_rows=combined_rows,base_rows=base_rows,targeted_rows_included=targeted_included,duplicates_removed=dupes,created_at=utc_now_iso())
    write_expansion_summary(summary)
    build_targeted_expansion_report(summary,validations)
    build_truth_score_delta_report([])
    return summary
