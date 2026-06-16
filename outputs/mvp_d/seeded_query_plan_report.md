# MVP-D Seeded Query Plan Report

## Summary
- total_queries: 20
- queries_by_seed: {"seed__000001": 8, "seed__000002": 8, "seed__000003": 4}
- queries_by_connector: {"hacker_news": 10, "github_issues": 8, "rss": 2}
- queries_by_type: {"persona_workflow": 8, "pain_expression": 6, "workaround_phrase": 2, "competitor_alternative": 2, "problem_phrase": 2}

## Query Examples

- query_seed__000001__000001 | seed=seed__000001 | pain=pain__000022 | hacker_news | persona_workflow | "investment researcher" "investment research workflow"
- query_seed__000001__000002 | seed=seed__000001 | pain=pain__000022 | github_issues | persona_workflow | investment researcher investment research workflow problem
- query_seed__000001__000003 | seed=seed__000001 | pain=pain__000022 | hacker_news | pain_expression | "information scattered" investment analyst
- query_seed__000001__000004 | seed=seed__000001 | pain=pain__000022 | github_issues | pain_expression | information scattered investment research
- query_seed__000001__000005 | seed=seed__000001 | pain=pain__000022 | hacker_news | workaround_phrase | "investment research" "spreadsheet" workaround
- query_seed__000001__000006 | seed=seed__000001 | pain=pain__000022 | hacker_news | competitor_alternative | investment research software alternative
- query_seed__000001__000007 | seed=seed__000001 | pain=pain__000022 | github_issues | problem_phrase | investment research workflow problem
- query_seed__000001__000008 | seed=seed__000001 | pain=pain__000022 | rss | persona_workflow | investment research workflow AI tool
- query_seed__000002__000001 | seed=seed__000002 | pain=pain__000023 | hacker_news | persona_workflow | "investment researcher" "investment research workflow"
- query_seed__000002__000002 | seed=seed__000002 | pain=pain__000023 | github_issues | persona_workflow | investment researcher investment research workflow problem
- query_seed__000002__000003 | seed=seed__000002 | pain=pain__000023 | hacker_news | pain_expression | "manual workflow" investment analyst
- query_seed__000002__000004 | seed=seed__000002 | pain=pain__000023 | github_issues | pain_expression | manual workflow investment research
- query_seed__000002__000005 | seed=seed__000002 | pain=pain__000023 | hacker_news | workaround_phrase | "investment research" "spreadsheet" workaround
- query_seed__000002__000006 | seed=seed__000002 | pain=pain__000023 | hacker_news | competitor_alternative | investment research software alternative
- query_seed__000002__000007 | seed=seed__000002 | pain=pain__000023 | github_issues | problem_phrase | investment research workflow problem
- query_seed__000002__000008 | seed=seed__000002 | pain=pain__000023 | rss | persona_workflow | investment research workflow AI tool
- query_seed__000003__000001 | seed=seed__000003 | pain=pain__000024 | hacker_news | persona_workflow | "investment researcher" "investment research workflow"
- query_seed__000003__000002 | seed=seed__000003 | pain=pain__000024 | github_issues | persona_workflow | investment researcher investment research workflow problem
- query_seed__000003__000003 | seed=seed__000003 | pain=pain__000024 | hacker_news | pain_expression | "manual workflow" investment analyst
- query_seed__000003__000004 | seed=seed__000003 | pain=pain__000024 | github_issues | pain_expression | manual workflow investment research
