"""Combined input builder for Stage 3.3."""
from __future__ import annotations
import csv,hashlib
from pathlib import Path
from demand_radar.targeted_expansion.targeted_validator import load_validations
def build_combined_input(base_path='examples/real_signal_samples_stage26.csv',targeted_path=None,validation_path='data/processed/targeted_signal_validation.jsonl',output_path='examples/combined_signal_samples_stage33.csv'):
    base_path=Path(base_path)
    output_path=Path(output_path)
    output_path.parent.mkdir(parents=True,exist_ok=True)
    rows=[]
    fieldnames=[]
    if base_path.exists():
        with base_path.open(encoding='utf-8-sig',newline='') as f:
            reader=csv.DictReader(f)
            fieldnames=list(reader.fieldnames or [])
            for row in reader: rows.append(dict(row))
    seen=set()
    def _key(r): return hashlib.md5((str(r.get('url',''))+str(r.get('raw_text',''))[:200]).encode()).hexdigest()
    for r in rows: seen.add(_key(r))
    base_count=len(rows)
    included=0
    duplicates=0
    targeted_path2=Path(targeted_path) if targeted_path else None
    if targeted_path2 and targeted_path2.exists():
        validations=load_validations(validation_path)
        include_ids={v.target_signal_id for v in validations if v.include_in_combined_input}
        with targeted_path2.open(encoding='utf-8-sig',newline='') as f:
            reader=csv.DictReader(f)
            if not fieldnames and reader.fieldnames: fieldnames=list(reader.fieldnames)
            for row in reader:
                sig_id=row.get('target_signal_id','')
                if sig_id not in include_ids: continue
                k=_key(row)
                if k in seen: duplicates+=1; continue
                seen.add(k)
                if not row.get('batch_id'): row['batch_id']='batch_stage33_targeted'
                rows.append(dict(row))
                included+=1
    if not fieldnames and rows: fieldnames=list(rows[0].keys())
    with output_path.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fieldnames,extrasaction='ignore')
        writer.writeheader()
        for r in rows: writer.writerow(r)
    return {'base_rows':base_count,'targeted_rows_included':included,'combined_rows':len(rows),'duplicates_removed':duplicates}
