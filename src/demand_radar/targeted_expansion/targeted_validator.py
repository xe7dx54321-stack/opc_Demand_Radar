"""Validator for targeted signals (Stage 3.3)."""
from __future__ import annotations
import csv
from pathlib import Path
from demand_radar.targeted_expansion.targeted_schema import (
    TargetedSignalTemplateRow, TargetedSignalValidation,
)
from demand_radar.state.raw_store import next_ids, utc_now_iso

_PAY_KW = ["付费","预算","价格","费用","成本","pay","paid","price","subscription","budget","cost","fee"]
_WA_KW = ["人工","手工","手动","表格","excel","外包","脚本","替代","manual","spreadsheet","workaround","outsource"]

def _has_kw(text,kws):
    lo=text.lower()
    return any(k in lo for k in kws)

def validate_targeted_signals(input_path,output_path='data/processed/targeted_signal_validation.jsonl'):
    input_path=Path(input_path)
    output_path=Path(output_path)
    output_path.parent.mkdir(parents=True,exist_ok=True)
    if not input_path.exists(): return []
    rows=[]
    with input_path.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        for rd in reader:
            for lf in ('target_gap_types','suggested_keywords','domain_tags'):
                v=rd.get(lf,'')
                rd[lf]=[x.strip() for x in v.split('|') if x.strip()] if v else []
            for bf in ('is_synthetic','exclude_from_truth_scoring'):
                rd[bf]=str(rd.get(bf,'false')).lower() in ('true','1','yes')
            for of in ('target_truth_score_id','target_current_score','title','raw_text','url','source_name','source_type','published_at','language','desired_source_type','desired_language','source_note','signal_focus','expected_quality','collector_note'):
                if not rd.get(of): rd[of]=None
            if rd.get('target_current_score') is not None:
                try: rd['target_current_score']=float(rd['target_current_score'])
                except: rd['target_current_score']=None
            try: rows.append(TargetedSignalTemplateRow(**rd))
            except: pass
    ids=next_ids('targeted_val',[],len(rows))
    validations=[]
    for val_id,row in zip(ids,rows):
        errors,warnings,detected=[],[],[]
        if not row.target_group_id: errors.append('missing target_group_id')
        if not row.evidence_intent: errors.append('missing evidence_intent')
        if row.collection_status=='collected' and not (row.raw_text or '').strip(): errors.append('collected but raw_text empty')
        raw_filled=bool((row.raw_text or '').strip())
        if raw_filled and not (row.url or '').strip() and not (row.source_note or '').strip(): errors.append('no source_url and no source_note')
        if row.is_synthetic and not row.exclude_from_truth_scoring: errors.append('is_synthetic=true but exclude_from_truth_scoring=false')
        combined=' '.join(filter(None,[row.raw_text,row.title,row.source_note]))
        if row.collection_status=='collected' and combined.strip():
            if row.evidence_intent in ('paid_alternative','budget_signal'):
                if not _has_kw(combined,_PAY_KW): warnings.append('paid intent but no payment keywords')
                else: detected.append('payment_signal')
            if row.evidence_intent in ('manual_workaround','current_solution'):
                if not _has_kw(combined,_WA_KW): warnings.append('workaround intent but no workaround keywords')
                else: detected.append('workaround_signal')
        if row.is_synthetic and row.exclude_from_truth_scoring: status,include='excluded',False
        elif errors: status,include='invalid',False
        elif warnings: status,include='warning',True
        elif row.collection_status=='pending': status,include='warning',False
        else: status,include='valid',True
        validations.append(TargetedSignalValidation(validation_id=val_id,target_signal_id=row.target_signal_id,target_group_id=row.target_group_id,evidence_intent=row.evidence_intent,status=status,validation_errors=errors,validation_warnings=warnings,matched_gap_types=row.target_gap_types,detected_signal_types=detected,include_in_combined_input=include,created_at=utc_now_iso()))
    output_path.write_text(chr(10).join(v.model_dump_json() for v in validations)+chr(10),encoding='utf-8')
    return validations

def load_validations(path='data/processed/targeted_signal_validation.jsonl'):
    path=Path(path)
    if not path.exists(): return []
    result=[]
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.strip():
            try: result.append(TargetedSignalValidation.model_validate_json(line))
            except: pass
    return result
