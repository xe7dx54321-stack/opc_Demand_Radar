# Radar MVP-A Live Acceptance Report

## Run Metadata

- Domain: ai_investment_tracking
- Radar commit: 30f88c6
- Foundation commit: b6d23bc
- Generated at: 2026-06-16T00:48:24Z

## Summary

- live_acquisition_succeeded: YES
- evidence_pack_draft_generated: YES
- r1_validation_ran: YES (136 items, all warning — expected at draft stage)
- draft_csv_path: examples/real_evidence_pack_ai_investment_tracking_draft.csv
- acquisition_report: outputs/acquisition/acquisition_report.md
- radar_report: outputs/radar/radar_report.md

## Core Metrics

- raw_signals: 163
- unique_signals: 143
- duplicates: 20
- evidence_candidates: 143
- valid_candidates: 134
- warning_candidates: 0
- invalid_candidates: 9 (all: raw_text too short)
- source_url_present: 143 / 143 (100%)
- placeholder_count: 1 (manual URL seed sample)
- synthetic_count: 0
- draft_csv_rows: 134

## By Source

- hacker_news_ai_investment: 60 signals
- github_issues_research_automation: 80 signals
- rss_ai_research_feeds: 20 signals
- manual_urls_ai_investment: 3 signals (seed samples, not scored)

## By Source Type

- community_discussion (HN): 60
- github_issue: 63 (after dedupe within GitHub source)
- rss: 20

## Detected Signal Types

- workflow_signal: 91 candidates
- paid_signal: 74 candidates
- time_cost_signal: 72 candidates
- workaround_signal: 63 candidates

## R1 Validation on Draft

- status: ran
- items: 136
- valid: 0 (expected — draft has empty persona/pain_type/evidence_quote)
- warning: 136 (expected at draft stage)
- invalid: 0

> Draft items are 'warning' because business fields (persona, workflow_stage, pain_type, evidence_quote)
> are empty — these need to be filled either manually or by MVP-B LLM extraction.
> This is correct behavior for the draft stage.

## Product Acceptance

- Did system acquire external signals? YES — 163 raw from 3 live sources
- Are candidates real? YES — all have source_url to traceable HN/GitHub/RSS pages
- Are candidates traceable? YES — 143/143 have source_url
- Are placeholders excluded from scoring? YES — 1 placeholder (SAMPLE) present, exclude_from_scoring=true
- Are there enough valid candidates for MVP-B? YES — 134 valid candidates

## Highlighted Demand Signals

Top candidates that most strongly match ai_investment_tracking domain:

1. **ThesisBoard – Trello for Investment Research** (HN community_discussion)
   - Equity portfolio manager describes pain with research workflow automation
   - Direct domain match: investment research + AI tooling

2. **Meticulate (YC W24) – LLM pipelines for business research** (HN)
   - Finance professionals research workflows, market sizing, competitive landscape
   - Strong commercial signal: YC-backed, targeting finance

3. **OpenCode-finance – prompt a ticker, get analyst report** (GitHub)
   - Analyst report generation automation
   - Direct match: investment research + AI automation

4. **Show HN: I built Deep Research for stocks** (HN)
   - Amateur investor using AI for investment candidate research
   - Clear workaround: built own tool because existing tools insufficient

5. **Launch HN: AnswerGrid (YC S24) – Web research tool** (HN)
   - Research automation for business/investment use cases
   - Shows market: multiple YC companies tackling same space

## Known Issues

### Radar-side Issues
- run-radar CLI re-runs acquisition (makes new network calls); workaround: use use_cached_acquisition=True in Python
- demand-radar CLI entrypoint is stale (installed before MVP-A); CLI commands still work via Python direct calls
- R1 validator marks all draft items as 'warning' (missing business fields) — this is expected behavior, not a bug

### Foundation Feedback (b6d23bc)
- HN RSS connector uses Algolia API; returns story text or title only (no full article body)
- Some signals have raw_text = title only (< 80 chars) → 9 invalid candidates
- GitHub Issues connector works without token (60 req/h rate limit applies)
- manual_url connector does not extract page text without extractor; uses URL/notes as text

### Source/Query Issues
- HN queries ('AI startup tracking', 'VC deal sourcing tools') return broad results
- Top 10 includes off-domain items (PlanEat AI, security research)
- Need domain-specific post-filtering in MVP-B to improve signal-to-noise

## Engineering & Product Acceptance

- engineering_acceptance: **PASS**
  - All 3 pipeline steps ran successfully
  - raw_signals > 0 ✅
  - unique_signals > 0 ✅
  - valid_candidates > 0 (134) ✅
  - synthetic_count = 0 ✅
  - placeholder excluded from scoring ✅
  - reports generated ✅

- product_acceptance: **PARTIAL**
  - Reason: signal quality is mixed — system acquires real signals but keyword-based signal detection is too broad
  - 'PlanEat AI', 'security research' items rank in top 10 despite being off-domain
  - Domain-specific filtering and persona matching needed (MVP-B LLM extraction)
  - Investment-specific signals (ThesisBoard, Meticulate, OpenCode-finance) ARE present and relevant

## Next Recommended Action

> **MVP-B is unblocked.** Foundation is working. 134 real candidates with source URLs ready.
> Priority for MVP-B: run pain extraction LLM on draft candidates to fill persona/pain_type/evidence_quote.
> Also add domain-specific post-filtering to improve signal-to-noise before extraction.