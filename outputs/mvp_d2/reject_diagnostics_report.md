# MVP-D2 Reject Diagnostics Report

## Summary
- total_rejected: 28
- total_candidates: 37
- by_seed: {"seed__000001": 25, "seed__000002": 3}
- by_query_type: {"persona_workflow": 10, "pain_expression": 11, "competitor_alternative": 2, "problem_phrase": 5}
- by_source_type: {"github_issue": 24, "community_discussion": 2, "rss": 2}
- by_reject_category: {"generic_article": 12, "domain_out": 3, "technical_issue_not_business_pain": 11, "raw_text_too_thin": 2}
- by_raw_text_quality: {"adequate": 2, "rich": 24, "too_thin": 2}
- by_candidate_usefulness: {"useful_for_market_context": 23, "useful_for_competitor_map": 1, "not_useful": 4}
- source_quality_distribution: {"low": 15, "medium": 13}

## Top Bad Queries
- investment researcher investment research workflow problem: 8
- information scattered investment research: 8
- investment research workflow problem: 5
- manual workflow investment research: 3
- investment research software alternative: 2
- investment research workflow AI tool: 2

## Top Promising Queries
- none

## Diagnostics
### reject_diag_000001
- candidate_id: mvp_d_cand__000001
- seed_id: seed__000001
- query_id: query_seed__000001__000002
- query: investment researcher investment research workflow problem
- query_type: persona_workflow
- source_type: github_issue
- connector: github_issues
- raw_text_chars: 784
- raw_text_quality: adequate
- reject_category: generic_article
- source_quality: low
- candidate_usefulness: useful_for_market_context
- llm_reject_reason: domain relevance excluded or score too low (0.05)
- note: 来自 seed__000001 的查询「investment researcher investment research workflow problem」在 github_issue 上命中该候选，raw_text 质量为 adequate。候选更像泛资讯/摘要内容，缺少具体用户、工作流和痛点证据。
- title: Daily Content Summary 2026-06-16
- source_url: https://github.com/jhengy/content-aggregator/issues/520

### reject_diag_000002
- candidate_id: mvp_d_cand__000002
- seed_id: seed__000001
- query_id: query_seed__000001__000002
- query: investment researcher investment research workflow problem
- query_type: persona_workflow
- source_type: github_issue
- connector: github_issues
- raw_text_chars: 135330
- raw_text_quality: rich
- reject_category: domain_out
- source_quality: low
- candidate_usefulness: useful_for_competitor_map
- llm_reject_reason: domain relevance excluded or score too low (0.05)
- note: 来自 seed__000001 的查询「investment researcher investment research workflow problem」在 github_issue 上命中该候选，raw_text 质量为 rich。候选内容与投资研究工作流相关性不足，LLM 域相关评分过低。
- title: [bluesky] engagement-ledger
- source_url: https://github.com/tobyrowland/update_ai_analysis/issues/349

### reject_diag_000003
- candidate_id: mvp_d_cand__000003
- seed_id: seed__000001
- query_id: query_seed__000001__000002
- query: investment researcher investment research workflow problem
- query_type: persona_workflow
- source_type: github_issue
- connector: github_issues
- raw_text_chars: 65516
- raw_text_quality: rich
- reject_category: generic_article
- source_quality: low
- candidate_usefulness: useful_for_market_context
- llm_reject_reason: domain relevance excluded or score too low (0.05)
- note: 来自 seed__000001 的查询「investment researcher investment research workflow problem」在 github_issue 上命中该候选，raw_text 质量为 rich。候选更像泛资讯/摘要内容，缺少具体用户、工作流和痛点证据。
- title: 🦞 OpenClaw Ecosystem Digest 2026-06-16
- source_url: https://github.com/DenisZheng/agents-radar/issues/1226

### reject_diag_000004
- candidate_id: mvp_d_cand__000004
- seed_id: seed__000001
- query_id: query_seed__000001__000002
- query: investment researcher investment research workflow problem
- query_type: persona_workflow
- source_type: github_issue
- connector: github_issues
- raw_text_chars: 21577
- raw_text_quality: rich
- reject_category: technical_issue_not_business_pain
- source_quality: medium
- candidate_usefulness: useful_for_market_context
- llm_reject_reason: domain relevance excluded or score too low (0.00)
- note: 来自 seed__000001 的查询「investment researcher investment research workflow problem」在 github_issue 上命中该候选，raw_text 质量为 rich。候选主要是技术 issue 或工程任务，不是投资研究业务痛点。
- title: New ETL/metadat stack
- source_url: https://github.com/calypr/calypr_etl_pod/issues/59

### reject_diag_000005
- candidate_id: mvp_d_cand__000006
- seed_id: seed__000001
- query_id: query_seed__000001__000002
- query: investment researcher investment research workflow problem
- query_type: persona_workflow
- source_type: github_issue
- connector: github_issues
- raw_text_chars: 2193
- raw_text_quality: rich
- reject_category: technical_issue_not_business_pain
- source_quality: medium
- candidate_usefulness: useful_for_market_context
- llm_reject_reason: domain relevance excluded or score too low (0.05)
- note: 来自 seed__000001 的查询「investment researcher investment research workflow problem」在 github_issue 上命中该候选，raw_text 质量为 rich。候选主要是技术 issue 或工程任务，不是投资研究业务痛点。
- title: [ONBOARD: 2 RTC] Star + Compare RustChain to Another Blockchain Project
- source_url: https://github.com/Scottcjn/rustchain-bounties/issues/2786

### reject_diag_000006
- candidate_id: mvp_d_cand__000007
- seed_id: seed__000001
- query_id: query_seed__000001__000002
- query: investment researcher investment research workflow problem
- query_type: persona_workflow
- source_type: github_issue
- connector: github_issues
- raw_text_chars: 65533
- raw_text_quality: rich
- reject_category: generic_article
- source_quality: low
- candidate_usefulness: useful_for_market_context
- llm_reject_reason: domain relevance excluded or score too low (0.05)
- note: 来自 seed__000001 的查询「investment researcher investment research workflow problem」在 github_issue 上命中该候选，raw_text 质量为 rich。候选更像泛资讯/摘要内容，缺少具体用户、工作流和痛点证据。
- title: 🦞 OpenClaw Ecosystem Digest 2026-06-15
- source_url: https://github.com/DenisZheng/agents-radar/issues/1212

### reject_diag_000007
- candidate_id: mvp_d_cand__000008
- seed_id: seed__000001
- query_id: query_seed__000001__000002
- query: investment researcher investment research workflow problem
- query_type: persona_workflow
- source_type: github_issue
- connector: github_issues
- raw_text_chars: 65563
- raw_text_quality: rich
- reject_category: generic_article
- source_quality: low
- candidate_usefulness: useful_for_market_context
- llm_reject_reason: domain relevance excluded or score too low (0.05)
- note: 来自 seed__000001 的查询「investment researcher investment research workflow problem」在 github_issue 上命中该候选，raw_text 质量为 rich。候选更像泛资讯/摘要内容，缺少具体用户、工作流和痛点证据。
- title: 🦞 OpenClaw Ecosystem Digest 2026-06-15
- source_url: https://github.com/duanyytop/agents-radar/issues/1639

### reject_diag_000008
- candidate_id: mvp_d_cand__000009
- seed_id: seed__000001
- query_id: query_seed__000001__000002
- query: investment researcher investment research workflow problem
- query_type: persona_workflow
- source_type: github_issue
- connector: github_issues
- raw_text_chars: 65553
- raw_text_quality: rich
- reject_category: generic_article
- source_quality: low
- candidate_usefulness: useful_for_market_context
- llm_reject_reason: domain relevance excluded or score too low (0.05)
- note: 来自 seed__000001 的查询「investment researcher investment research workflow problem」在 github_issue 上命中该候选，raw_text 质量为 rich。候选更像泛资讯/摘要内容，缺少具体用户、工作流和痛点证据。
- title: 📊 AI CLI Tools Digest 2026-06-06
- source_url: https://github.com/QYQAQ/agents-radar/issues/233

### reject_diag_000009
- candidate_id: mvp_d_cand__000010
- seed_id: seed__000001
- query_id: query_seed__000001__000004
- query: information scattered investment research
- query_type: pain_expression
- source_type: github_issue
- connector: github_issues
- raw_text_chars: 4469
- raw_text_quality: rich
- reject_category: generic_article
- source_quality: low
- candidate_usefulness: useful_for_market_context
- llm_reject_reason: domain relevance excluded or score too low (0.05)
- note: 来自 seed__000001 的查询「information scattered investment research」在 github_issue 上命中该候选，raw_text 质量为 rich。候选更像泛资讯/摘要内容，缺少具体用户、工作流和痛点证据。
- title: Capstone: the manifold dictionary learner for LLMs at scale — staged architecture, the structure ladder, and the blocker map
- source_url: https://github.com/SauersML/gam/issues/977

### reject_diag_000010
- candidate_id: mvp_d_cand__000011
- seed_id: seed__000001
- query_id: query_seed__000001__000004
- query: information scattered investment research
- query_type: pain_expression
- source_type: github_issue
- connector: github_issues
- raw_text_chars: 39949
- raw_text_quality: rich
- reject_category: technical_issue_not_business_pain
- source_quality: medium
- candidate_usefulness: useful_for_market_context
- llm_reject_reason: domain relevance excluded or score too low (0.05)
- note: 来自 seed__000001 的查询「information scattered investment research」在 github_issue 上命中该候选，raw_text 质量为 rich。候选主要是技术 issue 或工程任务，不是投资研究业务痛点。
- title: Design: WorkerSession — separate execution truth from card views (provider trait, principals, reaper, headless testing)
- source_url: https://github.com/keanji-x/neige-calm/issues/679

### reject_diag_000011
- candidate_id: mvp_d_cand__000012
- seed_id: seed__000001
- query_id: query_seed__000001__000004
- query: information scattered investment research
- query_type: pain_expression
- source_type: github_issue
- connector: github_issues
- raw_text_chars: 7903
- raw_text_quality: rich
- reject_category: technical_issue_not_business_pain
- source_quality: medium
- candidate_usefulness: useful_for_market_context
- llm_reject_reason: domain relevance excluded or score too low (0.05)
- note: 来自 seed__000001 的查询「information scattered investment research」在 github_issue 上命中该候选，raw_text 质量为 rich。候选主要是技术 issue 或工程任务，不是投资研究业务痛点。
- title: [R1N Gate] XuanLing Core Hardening and Runtime Consolidation
- source_url: https://github.com/chenchienheng/DCP-Framework/issues/185

### reject_diag_000012
- candidate_id: mvp_d_cand__000013
- seed_id: seed__000001
- query_id: query_seed__000001__000004
- query: information scattered investment research
- query_type: pain_expression
- source_type: github_issue
- connector: github_issues
- raw_text_chars: 2076
- raw_text_quality: rich
- reject_category: generic_article
- source_quality: low
- candidate_usefulness: useful_for_market_context
- llm_reject_reason: domain relevance excluded or score too low (0.05)
- note: 来自 seed__000001 的查询「information scattered investment research」在 github_issue 上命中该候选，raw_text 质量为 rich。候选更像泛资讯/摘要内容，缺少具体用户、工作流和痛点证据。
- title: [Tracker] Propose a cookbook example (selective intake)
- source_url: https://github.com/open-multi-agent/open-multi-agent/issues/147

### reject_diag_000013
- candidate_id: mvp_d_cand__000014
- seed_id: seed__000001
- query_id: query_seed__000001__000004
- query: information scattered investment research
- query_type: pain_expression
- source_type: github_issue
- connector: github_issues
- raw_text_chars: 65574
- raw_text_quality: rich
- reject_category: generic_article
- source_quality: low
- candidate_usefulness: useful_for_market_context
- llm_reject_reason: domain relevance excluded or score too low (0.05)
- note: 来自 seed__000001 的查询「information scattered investment research」在 github_issue 上命中该候选，raw_text 质量为 rich。候选更像泛资讯/摘要内容，缺少具体用户、工作流和痛点证据。
- title: 🦞 OpenClaw Ecosystem Digest 2026-06-16
- source_url: https://github.com/QYQAQ/agents-radar/issues/372

### reject_diag_000014
- candidate_id: mvp_d_cand__000015
- seed_id: seed__000001
- query_id: query_seed__000001__000004
- query: information scattered investment research
- query_type: pain_expression
- source_type: github_issue
- connector: github_issues
- raw_text_chars: 12563
- raw_text_quality: rich
- reject_category: generic_article
- source_quality: low
- candidate_usefulness: useful_for_market_context
- llm_reject_reason: domain relevance excluded or score too low (0.05)
- note: 来自 seed__000001 的查询「information scattered investment research」在 github_issue 上命中该候选，raw_text 质量为 rich。候选更像泛资讯/摘要内容，缺少具体用户、工作流和痛点证据。
- title: 🌐 Official AI Content Report 2026-06-09
- source_url: https://github.com/QYQAQ/agents-radar/issues/261

### reject_diag_000015
- candidate_id: mvp_d_cand__000016
- seed_id: seed__000001
- query_id: query_seed__000001__000004
- query: information scattered investment research
- query_type: pain_expression
- source_type: github_issue
- connector: github_issues
- raw_text_chars: 11127
- raw_text_quality: rich
- reject_category: generic_article
- source_quality: low
- candidate_usefulness: useful_for_market_context
- llm_reject_reason: domain relevance excluded or score too low (0.05)
- note: 来自 seed__000001 的查询「information scattered investment research」在 github_issue 上命中该候选，raw_text 质量为 rich。候选更像泛资讯/摘要内容，缺少具体用户、工作流和痛点证据。
- title: 🌐 Official AI Content Report 2026-06-11
- source_url: https://github.com/DenisZheng/agents-radar/issues/1140

### reject_diag_000016
- candidate_id: mvp_d_cand__000018
- seed_id: seed__000001
- query_id: query_seed__000001__000004
- query: information scattered investment research
- query_type: pain_expression
- source_type: github_issue
- connector: github_issues
- raw_text_chars: 441
- raw_text_quality: adequate
- reject_category: domain_out
- source_quality: low
- candidate_usefulness: not_useful
- llm_reject_reason: domain relevance excluded or score too low (0.05)
- note: 来自 seed__000001 的查询「information scattered investment research」在 github_issue 上命中该候选，raw_text 质量为 adequate。候选内容与投资研究工作流相关性不足，LLM 域相关评分过低。
- title: Announcements
- source_url: https://github.com/PySimpleGUI/PySimpleGUI/issues/142

### reject_diag_000017
- candidate_id: mvp_d_cand__000019
- seed_id: seed__000001
- query_id: query_seed__000001__000006
- query: investment research software alternative
- query_type: competitor_alternative
- source_type: community_discussion
- connector: hacker_news
- raw_text_chars: 6481
- raw_text_quality: rich
- reject_category: generic_article
- source_quality: medium
- candidate_usefulness: useful_for_market_context
- llm_reject_reason: domain relevance excluded or score too low (0.05)
- note: 来自 seed__000001 的查询「investment research software alternative」在 community_discussion 上命中该候选，raw_text 质量为 rich。候选更像泛资讯/摘要内容，缺少具体用户、工作流和痛点证据。
- title: Launch HN: Double (YC W24) – Index Investing with 0% Expense Ratios
- source_url: https://news.ycombinator.com/item?id=42377018

### reject_diag_000018
- candidate_id: mvp_d_cand__000020
- seed_id: seed__000001
- query_id: query_seed__000001__000006
- query: investment research software alternative
- query_type: competitor_alternative
- source_type: community_discussion
- connector: hacker_news
- raw_text_chars: 13872
- raw_text_quality: rich
- reject_category: generic_article
- source_quality: medium
- candidate_usefulness: useful_for_market_context
- llm_reject_reason: domain relevance excluded or score too low (0.05)
- note: 来自 seed__000001 的查询「investment research software alternative」在 community_discussion 上命中该候选，raw_text 质量为 rich。候选更像泛资讯/摘要内容，缺少具体用户、工作流和痛点证据。
- title: Turning startup profits into 100% tax-free gains.
- source_url: https://news.ycombinator.com/item?id=2562170

### reject_diag_000019
- candidate_id: mvp_d_cand__000021
- seed_id: seed__000001
- query_id: query_seed__000001__000007
- query: investment research workflow problem
- query_type: problem_phrase
- source_type: github_issue
- connector: github_issues
- raw_text_chars: 1370
- raw_text_quality: rich
- reject_category: domain_out
- source_quality: low
- candidate_usefulness: not_useful
- llm_reject_reason: domain relevance excluded or score too low (0.05)
- note: 来自 seed__000001 的查询「investment research workflow problem」在 github_issue 上命中该候选，raw_text 质量为 rich。候选内容与投资研究工作流相关性不足，LLM 域相关评分过低。
- title: DarkSouls - PT and NRD
- source_url: https://github.com/NVIDIA-RTX/NRD/issues/100

### reject_diag_000020
- candidate_id: mvp_d_cand__000022
- seed_id: seed__000001
- query_id: query_seed__000001__000007
- query: investment research workflow problem
- query_type: problem_phrase
- source_type: github_issue
- connector: github_issues
- raw_text_chars: 1405
- raw_text_quality: rich
- reject_category: technical_issue_not_business_pain
- source_quality: medium
- candidate_usefulness: useful_for_market_context
- llm_reject_reason: domain relevance excluded or score too low (0.05)
- note: 来自 seed__000001 的查询「investment research workflow problem」在 github_issue 上命中该候选，raw_text 质量为 rich。候选主要是技术 issue 或工程任务，不是投资研究业务痛点。
- title: The future of content filtering (declarativeNetRequest, Manifest v3, and beyond)
- source_url: https://github.com/ungoogled-software/ungoogled-chromium/issues/662

### reject_diag_000021
- candidate_id: mvp_d_cand__000023
- seed_id: seed__000001
- query_id: query_seed__000001__000007
- query: investment research workflow problem
- query_type: problem_phrase
- source_type: github_issue
- connector: github_issues
- raw_text_chars: 15504
- raw_text_quality: rich
- reject_category: technical_issue_not_business_pain
- source_quality: medium
- candidate_usefulness: useful_for_market_context
- llm_reject_reason: domain relevance excluded or score too low (0.05)
- note: 来自 seed__000001 的查询「investment research workflow problem」在 github_issue 上命中该候选，raw_text 质量为 rich。候选主要是技术 issue 或工程任务，不是投资研究业务痛点。
- title: PRD: Migrate agents to Pydantic AI (adapter-first) — umbrella
- source_url: https://github.com/BartmossMurphy2077/MCP-Universe-KINIT/issues/3

### reject_diag_000022
- candidate_id: mvp_d_cand__000024
- seed_id: seed__000001
- query_id: query_seed__000001__000007
- query: investment research workflow problem
- query_type: problem_phrase
- source_type: github_issue
- connector: github_issues
- raw_text_chars: 15361
- raw_text_quality: rich
- reject_category: technical_issue_not_business_pain
- source_quality: medium
- candidate_usefulness: useful_for_market_context
- llm_reject_reason: domain relevance excluded or score too low (0.05)
- note: 来自 seed__000001 的查询「investment research workflow problem」在 github_issue 上命中该候选，raw_text 质量为 rich。候选主要是技术 issue 或工程任务，不是投资研究业务痛点。
- title: PRD: Complete Azure migration — evaluators, benchmark YAMLs, and Azure-only overnight runs
- source_url: https://github.com/BartmossMurphy2077/MCP-Universe-KINIT/issues/4

### reject_diag_000023
- candidate_id: mvp_d_cand__000025
- seed_id: seed__000001
- query_id: query_seed__000001__000007
- query: investment research workflow problem
- query_type: problem_phrase
- source_type: github_issue
- connector: github_issues
- raw_text_chars: 3986
- raw_text_quality: rich
- reject_category: technical_issue_not_business_pain
- source_quality: medium
- candidate_usefulness: useful_for_market_context
- llm_reject_reason: domain relevance excluded or score too low (0.05)
- note: 来自 seed__000001 的查询「investment research workflow problem」在 github_issue 上命中该候选，raw_text 质量为 rich。候选主要是技术 issue 或工程任务，不是投资研究业务痛点。
- title: [RFE] Standardize Pull Request, Merging workflow and branch protection rules
- source_url: https://github.com/flatcar/Flatcar/issues/1714

### reject_diag_000024
- candidate_id: mvp_d_cand__000030
- seed_id: seed__000001
- query_id: query_seed__000001__000008
- query: investment research workflow AI tool
- query_type: persona_workflow
- source_type: rss
- connector: rss
- raw_text_chars: 149
- raw_text_quality: too_thin
- reject_category: raw_text_too_thin
- source_quality: low
- candidate_usefulness: not_useful
- llm_reject_reason: domain relevance excluded or score too low (0.00)
- note: 来自 seed__000001 的查询「investment research workflow AI tool」在 rss 上命中该候选，raw_text 质量为 too_thin。候选原文过短，无法支撑痛点抽取。
- title: The time the x86 emulator team found code so bad they fixed it during emulation
- source_url: https://devblogs.microsoft.com/oldnewthing/20260615-00/?p=112419

### reject_diag_000025
- candidate_id: mvp_d_cand__000033
- seed_id: seed__000001
- query_id: query_seed__000001__000008
- query: investment research workflow AI tool
- query_type: persona_workflow
- source_type: rss
- connector: rss
- raw_text_chars: 146
- raw_text_quality: too_thin
- reject_category: raw_text_too_thin
- source_quality: low
- candidate_usefulness: not_useful
- llm_reject_reason: domain relevance excluded or score too low (0.00)
- note: 来自 seed__000001 的查询「investment research workflow AI tool」在 rss 上命中该候选，raw_text 质量为 too_thin。候选原文过短，无法支撑痛点抽取。
- title: Feds freaked over Fable 5 after simple 'fix this code' prompt, not jailbreak
- source_url: https://www.theregister.com/security/2026/06/15/feds-freaked-over-fable-5-after-simple-fix-this-code-prompt-not-jailbreak-says-researcher/5255827

### reject_diag_000026
- candidate_id: mvp_d_cand__000035
- seed_id: seed__000002
- query_id: query_seed__000002__000004
- query: manual workflow investment research
- query_type: pain_expression
- source_type: github_issue
- connector: github_issues
- raw_text_chars: 20643
- raw_text_quality: rich
- reject_category: technical_issue_not_business_pain
- source_quality: medium
- candidate_usefulness: useful_for_market_context
- llm_reject_reason: domain relevance excluded or score too low (0.05)
- note: 来自 seed__000002 的查询「manual workflow investment research」在 github_issue 上命中该候选，raw_text 质量为 rich。候选主要是技术 issue 或工程任务，不是投资研究业务痛点。
- title: docs: audit tracker for documentation and examples
- source_url: https://github.com/Vaquum/Limen/issues/619

### reject_diag_000027
- candidate_id: mvp_d_cand__000036
- seed_id: seed__000002
- query_id: query_seed__000002__000004
- query: manual workflow investment research
- query_type: pain_expression
- source_type: github_issue
- connector: github_issues
- raw_text_chars: 6785
- raw_text_quality: rich
- reject_category: technical_issue_not_business_pain
- source_quality: medium
- candidate_usefulness: useful_for_market_context
- llm_reject_reason: domain relevance excluded or score too low (0.05)
- note: 来自 seed__000002 的查询「manual workflow investment research」在 github_issue 上命中该候选，raw_text 质量为 rich。候选主要是技术 issue 或工程任务，不是投资研究业务痛点。
- title: Publish Akluma to Google Play Store via TWA (Trusted Web Activity)
- source_url: https://github.com/Ubeydu/akluma-your-smart-piggy-bank/issues/369

### reject_diag_000028
- candidate_id: mvp_d_cand__000037
- seed_id: seed__000002
- query_id: query_seed__000002__000004
- query: manual workflow investment research
- query_type: pain_expression
- source_type: github_issue
- connector: github_issues
- raw_text_chars: 27755
- raw_text_quality: rich
- reject_category: technical_issue_not_business_pain
- source_quality: medium
- candidate_usefulness: useful_for_market_context
- llm_reject_reason: domain relevance excluded or score too low (0.05)
- note: 来自 seed__000002 的查询「manual workflow investment research」在 github_issue 上命中该候选，raw_text 质量为 rich。候选主要是技术 issue 或工程任务，不是投资研究业务痛点。
- title: OmniVideo-100K: A Dataset for Audio-Visual Reasoning through Structured Scripts and Evidence Chains
- source_url: https://github.com/smellslikeml/NeMo-Curator/issues/2
