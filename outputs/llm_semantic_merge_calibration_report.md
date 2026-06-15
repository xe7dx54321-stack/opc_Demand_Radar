# LLM Semantic Merge Calibration Report

## Summary

- Merge candidates: 153
- Previous LLM auto confirmed: 0
- Calibrated LLM auto confirmed: 39
- Previous LLM auto rejected: 0
- Calibrated LLM auto rejected: 14
- Previous human exceptions: 102
- Calibrated human exceptions: 100
- Previous exception rate: 1.0
- Calibrated exception rate: 0.654
- AI reviewed groups before: 0
- AI reviewed groups after: 5
- Stage 3 readiness before: no
- Stage 3 readiness after: partial
- Generated at: 2026-06-15T15:37:16Z

## Failure Statistics (Stage 2.9E)

- LLM call failures: 1
- Truncated outputs detected: 0
- Parse errors (LLM output invalid): 1
- Repaired via partial extraction: 0

## Cache Metadata (Stage 2.9D)

- prompt_version: semantic_merge_judge_v2
- gate_policy_version: semantic_merge_gate_v2
- provider: responses_compatible
- cache_enabled: True
- cache_reads: 0
- cache_writes: 152
- cache_bypassed: 153
- stale_cache_prevented: 3
- force_rerun: True
- no_cache: False
- clear_cache_used: False

## Confidence Distribution

| Decision | Count | Min | P25 | Mean | Median | P75 | Max |
|---|---:|---:|---:|---:|---:|---:|---:|
| prev/confirm_merge | 0 | None | None | None | None | None | None |
| cal/confirm_merge | 41 | 0.82 | 0.85 | 0.867 | 0.87 | 0.88 | 0.92 |
| prev/reject_merge | 0 | None | None | None | None | None | None |
| cal/reject_merge | 14 | 0.82 | 0.83 | 0.839 | 0.84 | 0.85 | 0.85 |
| prev/maybe_merge | 102 | 0.55 | 0.55 | 0.55 | 0.55 | 0.55 | 0.55 |
| cal/maybe_merge | 98 | 0.0 | 0.55 | 0.577 | 0.58 | 0.62 | 0.65 |

## Gate Outcome Breakdown

| Source | Decision | Auto Confirm | Auto Reject | Human Exception |
|---|---|---:|---:|---:|
| prev_llm | confirm_merge | 0 | 0 | 0 |
| prev_llm | reject_merge | 0 | 0 | 0 |
| prev_llm | maybe_merge | 0 | 0 | 102 |
| cal_llm | confirm_merge | 39 | 0 | 2 |
| cal_llm | reject_merge | 0 | 14 | 0 |
| cal_llm | maybe_merge | 0 | 0 | 98 |

## Preflight Results

- OK: 153
- Repaired: 0
- Invalid: 0

## Threshold Impact

- Rejects unlocked by calibrated threshold: 6
- Confirms unlocked by calibrated threshold: 37
- Still in exception: 100

## Representative Examples

### Auto Confirm Example

Candidate: merge_candidate_000001
Clusters: cluster_000011 / cluster_000068
Confidence: 0.88
Reason: 两个cluster的用户角色（content_team）、工作流（content_production）、领域标签（content_production）完全一致，核心痛点均围绕内容选题过程中信息分散、人工整理低效展开，标题仅在「耗时过多」措辞上略有差异，实质描述的是同一需求场景。相似度各维度均在92分以上，整体相似度达97.7，合并依据充分。
Suggested Group Title: 内容团队在内容选题生产中遇到的「信息分散、人工整理低效、耗时过多」问题

### Auto Reject Example

Candidate: merge_candidate_000024
Clusters: cluster_000042 / cluster_000064
Confidence: 0.82
Reason: 两个cluster的用户角色（persona）虽然相同（founder），但工作流领域明显不同：cluster_a属于AI智能体工作流（ai_agent_workflow），cluster_b属于AI产业跟踪/投资研究（ai_investment_research）。前者的核心场景是在构建或使用AI agent过程中遇到需要人工干预的问题，后者的核心场景是在追踪AI行业动态/投资研究过程中的人工整

### Human Exception Example

Candidate: merge_candidate_000003
Decision: maybe_merge
Confidence: 0.62
Reason: 两个 cluster 的用户角色、领域标签、工作流家族完全一致（均为 content_team / content_production），标题和摘要高度相似，表面特征指向同一需求。但 cluster_b 的唯一证据来自招聘启事，且原文明确标注'信号质量偏弱'、'没有说反复工作、人工整理或效率问题'，这意味着 cluster_b 并未提供对核心痛点的直接支撑。cluster_a 有2条直接用户引语
Conflict Flags: ['weak_evidence', 'ambiguous_scope']

## Recommendation

- Enter Stage 3: partial
- AI reviewed groups: 5 (target >= 5)
- Exception rate: 0.654 (target <= 0.45)
- Consider further prompt calibration or threshold adjustment if groups < 5.
