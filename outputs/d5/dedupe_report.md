# D5 Dedupe Report

- original_pain_items: 46
- deduped_representatives: 13
- duplicate_groups: 12
- top_duplicate_domains: {'www.reddit.com': 8, 'www.youtube.com': 5, 'www.datatobrief.com': 4, 'carta.com': 4, 'www.allvuesystems.com': 4, 'www.goingvc.com': 4, 'www.marvin-labs.com': 4, 'n8n.io': 4, 'nvca.org': 4, 'conceptor.ai': 3}
- top_duplicate_urls: {'https://www.datatobrief.com/blog/build-ai-investment-research-workflow-2026': 4, 'https://www.youtube.com/watch?v=mSjL4kSPgJk': 4, 'https://carta.com/learn/private-funds/management/deal-flow/deal-sourcing': 4, 'https://www.allvuesystems.com/resources/a-guide-to-private-equity-deal-sourcing': 4, 'https://www.goingvc.com/post/beginners-guide-to-deal-sourcing': 4, 'https://www.marvin-labs.com/resources/equity-research-automation': 4, 'https://n8n.io/workflows/12949-generate-weekly-ai-equity-research-reports-with-google-sheets-fmp-newsapi-openai-and-gmail': 4, 'https://www.reddit.com/r/ValueInvesting/comments/14gqz52/whats_your_investment_analysis_workflow': 4, 'https://www.reddit.com/r/venturecapital/comments/1d2mctd/market_research_tool_for_vcs_and_other_investors': 4, 'https://nvca.org/careers/analyst': 4}

## Representative Selection
同 source_url 的多条 pain item 只形成一个 source group，并优先选择人工正向审核、证据强度高、来源权重高、quote 更完整的代表项。
非代表项保留在 deduped_pain_items.jsonl 中，但不会重复放大主题 evidence_count。
