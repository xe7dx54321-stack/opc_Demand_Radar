"""Reports for Stage 3.3 Targeted Evidence Expansion."""
from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from demand_radar.targeted_expansion.targeted_schema import TargetedExpansionSummary,TruthScoreDelta
def _now(): return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
def build_targeted_expansion_report(summary,validations,output_path='outputs/targeted_expansion_report.md'):
    output_path=Path(output_path)
    output_path.parent.mkdir(parents=True,exist_ok=True)
    lines=['# Targeted Evidence Expansion Report','','## Summary','']
    if summary:
        lines+=[f'- Template rows: {summary.template_rows}',f'- Filled targeted signals: {summary.filled_signals}',f'- Valid targeted signals: {summary.valid_signals}',f'- Warning targeted signals: {summary.warning_signals}',f'- Invalid targeted signals: {summary.invalid_signals}',f'- Excluded synthetic signals: {summary.excluded_synthetic}',f'- Combined input rows: {summary.combined_input_rows}',f'- Generated at: {_now()}','']
    else:
        lines+=[f'- Generated at: {_now()}','']
    lines+=['## Validation Summary','']
    from collections import Counter
    by_status=Counter(v.status for v in validations)
    by_intent=Counter(v.evidence_intent for v in validations if v.evidence_intent)
    for status,cnt in sorted(by_status.items()): lines.append(f'- {status}: {cnt}')
    lines+=['','### Evidence Intent Coverage','']
    for intent,cnt in sorted(by_intent.items()): lines.append(f'- {intent}: {cnt}')
    if validations:
        invalid=[v for v in validations if v.status=='invalid']
        if invalid:
            lines+=['','## Validation Issues','']
            for v in invalid[:10]:
                lines.append(f'- {v.target_signal_id}: {chr(44).join(v.validation_errors)}')
    output_path.write_text(chr(10).join(lines),encoding='utf-8')
def build_truth_score_delta_report(deltas,output_path='outputs/truth_score_delta_report.md'):
    output_path=Path(output_path)
    output_path.parent.mkdir(parents=True,exist_ok=True)
    if not deltas:
        output_path.write_text('# Truth Score Delta Report'+chr(10)+chr(10)+'No comparison available. Run run-stage33-full to generate before/after comparison.'+chr(10),encoding='utf-8')
        return
    improved=[d for d in deltas if d.delta and d.delta>0]
    declined=[d for d in deltas if d.delta and d.delta<0]
    new_strong=[d for d in deltas if d.after_truth_level=='strong' and d.before_truth_level!='strong']
    new_proceed=[d for d in deltas if d.after_next_action=='proceed_to_fit_scoring' and d.before_next_action!='proceed_to_fit_scoring']
    lines=['# Truth Score Delta Report','','## Summary','',f'- Compared candidates: {len(deltas)}',f'- Improved: {len(improved)}',f'- Declined: {len(declined)}',f'- Unchanged: {len(deltas)-len(improved)-len(declined)}',f'- New strong candidates: {len(new_strong)}',f'- New proceed_to_fit_scoring: {len(new_proceed)}',f'- Generated at: {_now()}','','## Candidate Deltas','']
    for d in sorted(deltas,key=lambda x:-(x.delta or 0)):
        delta_str=f'+{d.delta:.1f}' if d.delta and d.delta>0 else (f'{d.delta:.1f}' if d.delta else 'n/a')
        lines+=[f'### {d.group_title_zh}','',f'Before: {d.before_truth_score} ({d.before_truth_level}) -> {d.before_next_action}',f'After: {d.after_truth_score} ({d.after_truth_level}) -> {d.after_next_action}',f'Delta: {delta_str}','']
        if d.improved_dimensions: lines.append('Improved: '+', '.join(d.improved_dimensions))
        if d.remaining_gaps: lines.append('Remaining gaps: '+', '.join(d.remaining_gaps))
        lines.append('---')
        lines.append('')
    output_path.write_text(chr(10).join(lines),encoding='utf-8')
