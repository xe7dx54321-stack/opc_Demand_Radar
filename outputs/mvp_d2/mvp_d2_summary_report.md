# MVP-D2 Expansion Diagnostics & Query Calibration Summary

## Run Metadata
- generated_at: 2026-06-17T00:44:34Z
- radar_commit: a97ee58
- foundation_commit: b6d23bc
- provider: none
- model: none
- real_llm_run: false
- cache_enabled: true

## Problem Statement
- MVP-D selected_for_llm: 28
- MVP-D should_extract_true: 0
- MVP-D reject_count: 28

## Reject Diagnostics
- by_reject_category: {"generic_article": 12, "domain_out": 3, "technical_issue_not_business_pain": 11, "raw_text_too_thin": 2}
- by_source_type: {"github_issue": 24, "community_discussion": 2, "rss": 2}
- by_query_type: {"persona_workflow": 10, "pain_expression": 11, "competitor_alternative": 2, "problem_phrase": 5}
- by_raw_text_quality: {"adequate": 2, "rich": 24, "too_thin": 2}
- top_failure_patterns: ["generic_article: 12", "technical_issue_not_business_pain: 11", "domain_out: 3", "raw_text_too_thin: 2"]

## Source Strategy
- source_quality_scores: {"community_discussion": 0.07, "github_issue": 0.25, "rss": 0.23}
- keep: []
- deprioritize: ["rss"]
- use_only_for_context: ["github_issue"]
- needs_better_query: ["community_discussion"]
- needs_new_connector: []

## Query Calibration
- generated_v2_queries: 48
- query_types: {"pain_phrase": 10, "manual_workflow": 15, "complaint_phrase": 5, "spreadsheet_workaround": 8, "workaround_phrase": 6, "buying_intent": 4}
- example_queries: ["\"investment research workflow\" \"spreadsheet\"", "\"investment research workflow\" \"manual\"", "\"investment memo\" \"time consuming\"", "\"VC analyst\" \"due diligence\" \"spreadsheet\"", "\"VC analyst\" \"market research\" \"pain\"", "\"portfolio monitoring\" \"too much information\"", "\"portfolio monitoring\" \"hard to track\"", "\"deal sourcing\" \"manual research\"", "\"company tracking\" \"investment analyst\" \"spreadsheet\"", "\"equity research\" \"data collection\" \"manual\""]

## Calibrated Pilot
- ran_pilot: false
- blocked_reason: blocked_by_missing_search_provider
- raw_new_signals: 0
- unique_new_signals: 0
- selected_for_llm: 0
- should_extract_true: 0
- yield_rate: 0.0

## Acceptance
- engineering_acceptance: pass
- product_acceptance: partial
- can_rerun_seeded_expansion: true
- can_enter_second_review: false
- can_enter_foundation_source_upgrade: true
- reason: 诊断和 query v2 已生成，但 calibrated pilot 因缺少 search provider 或被跳过而未完成真实验证。

## Recommended Next Actions
- 接入一个可验证的 search provider 做小批量 URL pilot，不要直接新增 Foundation connector。
- 用 calibrated query v2 重跑 MVP-D seeded expansion，优先观察 community discussion 和 workaround 类命中。
- 降低 RSS 泛资讯在痛点证据发现中的优先级，仅用于市场上下文。
