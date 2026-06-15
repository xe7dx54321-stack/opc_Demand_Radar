# LLM Semantic Merge Comparison Report

## Summary

- Merge candidates: 102
- Rule-based judgments: 102
- LLM judgments: 102
- Rule-based auto confirmed: 0
- LLM auto confirmed: 0
- Rule-based auto rejected: 0
- LLM auto rejected: 0
- Rule-based human exceptions: 102
- LLM human exceptions: 102
- Rule-based exception rate: 100.0%
- LLM exception rate: 100.0%
- Rule-based AI reviewed groups: 0
- LLM AI reviewed groups: 0
- Readiness source: llm
- Generated at: 2026-06-15T06:29:30Z

## Decision Shift Matrix

| Rule-based \ LLM | confirm | reject | maybe |
|---|---:|---:|---:|
| confirm | 0 | 0 | 0 |
| reject | 0 | 0 | 0 |
| maybe | 0 | 0 | 102 |

## Improvements

- Candidates moved from maybe to auto_confirm: 0
- Candidates moved from maybe to auto_reject: 0
- New LLM reviewed groups: 0
- Exception rate reduction: 0.0%

## Potential Risks

- LLM confirms that rule-based rejected: 0
- LLM rejects that rule-based confirmed: 0
- Low-confidence LLM outputs (< 0.70): 102
- LLM call failures: 0

## Representative Examples

### 1. Rule-based maybe → LLM confirm

No examples in this run.

### 2. Rule-based maybe → LLM reject

No examples in this run.

### 3. LLM human exception

Candidate: merge_candidate_000001
Reason: AI 判断为暂不确定，需要人工裁决。
Conflict flags: none
