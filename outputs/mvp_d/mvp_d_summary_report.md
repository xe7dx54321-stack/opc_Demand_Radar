# MVP-D Seeded Evidence Expansion Summary

## Run Metadata
- generated_at: 2026-06-16T14:20:51Z
- radar_commit: c3a06e7
- foundation_commit: unknown
- provider: none
- model: none
- real_llm_run: false
- cache_enabled: true

## Seed Summary
- total_reviews: 5
- eligible_seeds: 4
- optional_seeds: 0
- excluded_reviews: 1
- selected_seed_ids: ["seed__000001", "seed__000002", "seed__000003", "seed__000004"]

## Query Plan
- total_queries: 20
- queries_by_seed: {"seed__000001": 8, "seed__000002": 8, "seed__000003": 4}
- queries_by_connector: {"hacker_news": 10, "github_issues": 8, "rss": 2}
- query_examples: ["\"investment researcher\" \"investment research workflow\"", "investment researcher investment research workflow problem", "\"information scattered\" investment analyst", "information scattered investment research", "\"investment research\" \"spreadsheet\" workaround"]

## Acquisition Results
- raw_new_signals: 104
- unique_new_signals: 40
- deduped_against_existing: 3
- allowed_by_real_signal_gate: 28
- blocked_by_real_signal_gate: 9
- source_url_present: 37

## Extraction Results
- selected_for_llm: 28
- should_extract_true: 0
- strong: 0
- medium: 0
- weak: 0
- reject: 28
- failures: 0
- cache_hits: 0

## Evidence Consolidation
- seeds_with_new_support: 0
- seeds_without_new_support: 4
- pursue_candidate: 0
- watch: 0
- needs_more_evidence: 2
- reject: 2

## Demand Themes
- theme_count: 4
- top_themes: [{"theme_title_zh": "retail investor / 自主管理个人投资组合的散户投资人 在 portfolio_monitoring_and_idea_generation 中的 workflow_friction + information_overload + tool_inadequacy 需求", "recommendation": "needs_more_evidence", "evidence_count": 1}, {"theme_title_zh": "equity portfolio manager / institutional allocator / investment analyst 在 investment research workflow management / thesis development 中的 workflow_fragmentation 需求", "recommendation": "needs_more_evidence", "evidence_count": 1}, {"theme_title_zh": "individual investor / retail investor with framework-driven research workflow 在 idea generation / investment screening 中的 workflow_inefficiency 需求", "recommendation": "reject", "evidence_count": 1}, {"theme_title_zh": "investment analyst / vc due diligence researcher / finance professional 在 pre-investment due diligence / market research 中的 time_cost + quality + access_cost 需求", "recommendation": "reject", "evidence_count": 1}]

## Acceptance
- engineering_acceptance: pass
- product_acceptance: pass
- can_enter_second_review: true
- can_enter_product_discovery: false
- reason: seeded evidence expansion produced actionable themes
