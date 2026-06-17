# MVP-D2 Source Quality Report

## Summary
- source_quality_scores: {"community_discussion": 0.07, "github_issue": 0.25, "rss": 0.23}
- keep: []
- deprioritize: ["rss"]
- use_only_for_context: ["github_issue"]
- needs_better_query: ["community_discussion"]
- needs_new_connector: []

## Key Findings
- 社区讨论数量太少但 source 类型仍值得保留，需要改用痛点/工作流 query。
- GitHub Issues 在 v1 中没有产生新增痛点证据，更适合作为技术/市场上下文或需要更严格 query。
- RSS 在 v1 中偏泛资讯，作为 pain evidence source 应降权。

## Scores

| Source Type | Connector | Candidates | LLM Processed | Extracted | Yield | Dominant Reject | Score | Recommendation |
|---|---|---:|---:|---:|---:|---|---:|---|
| community_discussion | hacker_news | 2 | 2 | 0 | 0.0000 | generic_article | 0.0700 | needs_better_query |
| github_issue | github_issues | 27 | 24 | 0 | 0.0000 | technical_issue_not_business_pain | 0.2500 | use_only_for_context |
| rss | rss | 8 | 2 | 0 | 0.0000 | raw_text_too_thin | 0.2300 | deprioritize |
