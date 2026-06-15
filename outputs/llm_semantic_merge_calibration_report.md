# LLM Semantic Merge Calibration Report

## Summary

- Merge candidates: 131
- Previous LLM auto confirmed: 0
- Calibrated LLM auto confirmed: 30
- Previous LLM auto rejected: 0
- Calibrated LLM auto rejected: 17
- Previous human exceptions: 102
- Calibrated human exceptions: 84
- Previous exception rate: 1.0
- Calibrated exception rate: 0.641
- AI reviewed groups before: 0
- AI reviewed groups after: 5
- Stage 3 readiness before: no
- Stage 3 readiness after: partial
- Generated at: 2026-06-15T08:59:07Z

## Failure Statistics (Stage 2.9E)

- LLM call failures: 0
- Truncated outputs detected: 0
- Parse errors (LLM output invalid): 0
- Repaired via partial extraction: 0

## Cache Metadata (Stage 2.9D)

- prompt_version: semantic_merge_judge_v2
- gate_policy_version: semantic_merge_gate_v2
- provider: responses_compatible
- cache_enabled: True
- cache_reads: 0
- cache_writes: 131
- cache_bypassed: 131
- stale_cache_prevented: 6
- force_rerun: True
- no_cache: False
- clear_cache_used: False

## Confidence Distribution

| Decision | Count | Min | P25 | Mean | Median | P75 | Max |
|---|---:|---:|---:|---:|---:|---:|---:|
| prev/confirm_merge | 0 | None | None | None | None | None | None |
| cal/confirm_merge | 32 | 0.82 | 0.85 | 0.868 | 0.87 | 0.88 | 0.93 |
| prev/reject_merge | 0 | None | None | None | None | None | None |
| cal/reject_merge | 17 | 0.82 | 0.83 | 0.843 | 0.85 | 0.85 | 0.85 |
| prev/maybe_merge | 102 | 0.55 | 0.55 | 0.55 | 0.55 | 0.55 | 0.55 |
| cal/maybe_merge | 82 | 0.52 | 0.55 | 0.578 | 0.58 | 0.62 | 0.62 |

## Gate Outcome Breakdown

| Source | Decision | Auto Confirm | Auto Reject | Human Exception |
|---|---|---:|---:|---:|
| prev_llm | confirm_merge | 0 | 0 | 0 |
| prev_llm | reject_merge | 0 | 0 | 0 |
| prev_llm | maybe_merge | 0 | 0 | 102 |
| cal_llm | confirm_merge | 30 | 0 | 2 |
| cal_llm | reject_merge | 0 | 17 | 0 |
| cal_llm | maybe_merge | 0 | 0 | 82 |

## Preflight Results

- OK: 131
- Repaired: 0
- Invalid: 0

## Threshold Impact

- Rejects unlocked by calibrated threshold: 8
- Confirms unlocked by calibrated threshold: 29
- Still in exception: 84

## Representative Examples

### Auto Confirm Example

Candidate: merge_candidate_000001
Clusters: cluster_000011 / cluster_000068
Confidence: 0.88
Reason: 两个 cluster 的用户角色（content_team）、工作流（content_production）、领域标签（content_production）完全一致，核心痛点均为内容选题过程中信息分散、人工整理低效的问题。标题高度相似（仅在「耗时过多」措辞上有细微差异），摘要结构几乎相同。唯一差异在于证据质量：cluster_a 的代表性引用为直接用户痛点陈述（公众号/播客/竞品页面信息分散、人
Suggested Group Title: 内容团队在内容选题生产中遇到的「信息分散、人工整理低效、耗时过多」问题

### Auto Reject Example

Candidate: merge_candidate_000018
Clusters: cluster_000038 / cluster_000085
Confidence: 0.85
Reason: 两个cluster的用户角色明显不同：cluster_a的persona为运营（operator），cluster_b的persona为开发者（developer）。虽然两者都处于ai_agent_workflow领域，且都涉及

### Human Exception Example

Candidate: merge_candidate_000003
Decision: maybe_merge
Confidence: 0.62
Reason: 两个cluster的用户角色（content_team）、领域标签（content_production）、工作流（content_production）完全相同，表面相似度极高（96.7）。然而，cluster_b的唯一证据来源是一则招聘启事，且证据本身已明确标注「信号质量偏弱」，既未直接描述信息分散或人工整理的痛点，也未反映真实用户的工作流困扰。cluster_a有2条来自真实用户陈述的直接痛
Conflict Flags: ['weak_evidence', 'ambiguous_scope']

## Recommendation

- Enter Stage 3: partial
- AI reviewed groups: 5 (target >= 5)
- Exception rate: 0.641 (target <= 0.45)
- Consider further prompt calibration or threshold adjustment if groups < 5.
