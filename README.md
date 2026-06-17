# Domain-Bounded Demand Radar
The core rule remains: no evidence quote, no pain point.

## Stage 2.8 Scope

Stage 2.8: Activate AI Semantic Merge as Main Pipeline.

This layer upgrades AI semantic merge from an auxiliary module to the primary merge judgment pathway. The system no longer expects humans to approve every merge candidate one by one. Instead, AI automatically processes high-confidence decisions and routes edge cases to a human exception queue.

### Why not manual review for every candidate

1. Merge judgment is a semantic understanding task, not a mechanical approval task.
2. LLM is better suited than rule-based similarity for judging whether two demands belong to the same workflow.
3. Human reviewers should focus on exceptions and spot checks, not primary review.

### Pipeline

```text
demand_clusters
  -> cluster_merge_candidates
  -> semantic_merge_judge (AI)
  -> auto_confirm: ai_reviewed_cluster_groups
  -> auto_reject: recorded in semantic_merge_judgments
  -> human_exception: human_exception_queue
  -> Stage 3 readiness uses ai_reviewed_groups + human_reviewed_groups
```

### Judge modes

`rule_based_stub` (default): Offline, no API calls. Uses field similarity scores, persona overlap, and workflow family to determine confirm / reject / maybe. Suitable for local testing.

`llm`: Calls an OpenAI-compatible API with a structured JSON output prompt. Requires `DEMAND_RADAR_LLM_BASE_URL` and `DEMAND_RADAR_LLM_API_KEY` environment variables and a `model` name in `configs/semantic_merge_config.yaml`. If the API call fails, the judgment falls back to `human_exception` automatically without interrupting the pipeline.

### Configuring real LLM

Set environment variables (do not commit keys):

```bash
export DEMAND_RADAR_LLM_BASE_URL=https://api.openai.com/v1
export DEMAND_RADAR_LLM_API_KEY=sk-...
```

Update `configs/semantic_merge_config.yaml`:

```yaml
semantic_merge:
  mode: llm
  llm:
    model: gpt-4o
```

### Confidence Gate

| Condition | Auto Action |
|---|---|
| confirm_merge, confidence >= 0.85, no severe conflict_flags, title + summary present | auto_confirm |
| reject_merge, confidence >= 0.85 | auto_reject |
| maybe_merge, or confidence < threshold, or severe conflict_flags, or LLM failure | human_exception |

Severe conflict flags: `different_persona`, `different_workflow`, `different_pain`, `weak_evidence`, `ambiguous_scope`.

### AI Reviewed Groups

All `auto_confirm` judgments are connected via union-find to build `ai_reviewed_cluster_groups.jsonl`. Example: if A+B confirm and B+C confirm, the result is one group [A, B, C]. Groups are stored separately and never overwrite `demand_clusters.jsonl`.

### Human Exception Queue

All `human_exception` judgments are written to `data/processed/human_exception_queue.jsonl`. The Review UI provides an exception queue tab with five actions: confirm merge, reject merge, mark AI reason bad, defer, and request rerun. These actions write to `data/processed/semantic_merge_human_audits.jsonl` and do not modify AI judgments directly.

### Stage 3 Readiness

```text
effective_reviewed_groups = ai_reviewed_cluster_groups + human_reviewed_cluster_groups

Conditions for ready_for_truth_scoring = yes:
  raw_signals >= 50
  pain_points >= 35
  effective_reviewed_groups >= 5
  human_exception_rate <= 0.40
  auto_confirmed_groups >= 3
```

It adds:

- `configs/semantic_merge_config.yaml` (expanded with llm, thresholds, batch blocks)
- `data/processed/semantic_merge_judgments.jsonl`
- `data/processed/ai_reviewed_cluster_groups.jsonl`
- `data/processed/human_exception_queue.jsonl`
- `data/processed/semantic_merge_human_audits.jsonl`
- `outputs/semantic_merge_audit.md`
- `outputs/semantic_merge_judgment_report.md`
- `outputs/ai_reviewed_cluster_groups_report.md`
- `outputs/human_exception_queue_report.md`
- `demand-radar run-stage28`
- Review UI: AI Merge Judgment tab and Human Exception Queue tab
- `FakeLLMJudge` for unit testing without network calls

### Running Stage 2.8

```bash
demand-radar run-stage28 --input examples/real_signal_samples_stage26.csv
demand-radar review-ui --port 8502
```

# Domain-Bounded Demand Radar

This is an internal demand discovery tool.

Domain-Bounded Demand Radar is a local-first system for collecting manual demand signals, preserving raw evidence, normalizing text, extracting evidence-backed pain points, and quarantining weak or invalid outputs.

Stage 1 focuses on manual signal intake and pain extraction only.

No automated web crawling, clustering, scoring, or MVP generation is included in this stage.

Stage 1.5 adds real-signal calibration and LLM extractor readiness. It still does not call a real LLM or external API.

Stage 1.6 adds a local Streamlit Review UI for low-friction calibration review. The visible interface is Chinese-first for local review work. It is still an internal local tool, not a formal web app.

Stage 2 adds a lightweight Demand Clustering Loop and cluster review workflow. Demand clusters are candidate state only; truth scoring and fit scoring are still out of scope.

Stage 2.5 adds cluster merge suggestions and reviewed cluster groups. Merge suggestions are candidate state only; confirmed reviews generate reviewed groups without mutating `demand_clusters.jsonl`.

Stage 2.6 adds real-signal expansion and batch radar runs. It introduces batch fields for manual samples, runs the full pipeline on 50-100 signals, and reports batch-level extraction, clustering, merge, and Stage 3 readiness metrics.

Stage 2.8 activates AI semantic merge as the main pipeline. AI automatically processes high-confidence merge candidates and routes uncertain cases to a human exception queue. Human reviewers only handle exceptions and spot checks instead of approving every candidate one by one.

Stage 2.9 runs a real LLM semantic merge pilot. The system calls an OpenAI-compatible or Anthropic-compatible API to judge merge candidates with structured JSON output, strict schema and confidence gates, and a separate cache. Results are stored in llm_* paths so rule_based outputs are never overwritten. A comparison report shows decision shifts, exception rate changes, and new LLM reviewed groups.

MVP-D adds seeded evidence expansion from human-reviewed pain signals. It reads MVP-C reviews, selects true pains that need more evidence, generates targeted acquisition queries, runs existing HN/GitHub/RSS connectors, gates out placeholder/example/synthetic signals, reuses MVP-B relevance and extraction, and groups consolidated evidence into lightweight demand themes.

## Stage 1 Scope

The current pipeline is intentionally narrow:

```text
project skeleton
domain config
manual signal import
Raw State persistence
Cleaning / Normalization
Pain Extraction Loop
State Gate validation
Quarantine
Pain Points report
```

This stage does not include automated source collection, Reddit/HN/GitHub APIs, clustering, truth scoring, fit scoring, Top 10 demand candidates, web UI, vector databases, multi-agent orchestration, interview planning, or MVP generation.

## Stage 1.5 Scope

Stage 1.5: Real Signal Calibration & LLM Extractor Readiness.

This layer helps the team run 20-50 real or near-real manual samples through the Stage 1 pain extraction loop, record human review labels, and generate an extraction calibration report. The goal is to see what the current rule-based extractor gets right or wrong before adding a real structured-output LLM extractor.

It adds:

- `examples/real_signal_samples.csv`
- `configs/calibration_config.yaml`
- `data/processed/calibration_reviews.jsonl`
- `outputs/calibration_report.md`
- `prompts/llm_pain_extraction.md`
- `LLMExtractorStub`, which does not call external APIs

It still excludes automated crawling, clustering, truth scoring, fit scoring, Top Demand Candidates, and MVP generation.

## Stage 1.6 Scope

Stage 1.6: Review UI for Calibration.

This layer adds a local Chinese Streamlit interface for reviewing extracted pain points and quarantined items. It shows clean Chinese demand summaries, extraction fields, quarantine reasons, and the latest review status in one place. English source text is not shown in the main review view; use the source link when original-language verification is needed.

It adds:

- `demand-radar review-ui`
- `src/demand_radar/ui/review_app.py`
- `src/demand_radar/ui/review_service.py`
- `src/demand_radar/calibration/review_store.py`

The UI writes reviews to `data/processed/calibration_reviews.jsonl`. Reviews are feedback memory only: they do not edit raw signals, normalized signals, quarantine records, or `pain_points.jsonl`.

## Stage 2 Scope

Stage 2: Demand Clustering Loop & Cluster Review.

This layer groups extracted pain points into Chinese demand topic candidates using a lightweight rule and text-similarity approach. Singleton clusters are kept instead of being forced into weak groups, and cluster review feedback is stored separately from the generated cluster state.

It adds:

- `configs/clustering_config.yaml`
- `data/processed/demand_clusters.jsonl`
- `data/processed/cluster_reviews.jsonl`
- `data/quarantine/invalid_clusters.jsonl`
- `outputs/demand_clusters_report.md`
- `demand-radar run-cluster`
- `demand-radar build-cluster-report`
- `demand-radar run-stage2`

The Review UI now includes a `需求主题审核` tab. It shows Chinese demand titles, summaries, representative pain descriptions, evidence summaries, current alternatives, and cluster review buttons. Cluster reviews are feedback memory only: they do not mutate `demand_clusters.jsonl`.

## Stage 2.5 Scope

Stage 2.5: Cluster Merge Suggestions & Review Calibration.

This layer diagnoses which singleton or near-singleton demand clusters may belong to the same higher-level demand theme. It generates Chinese merge reasons, field-level similarity diagnostics, and representative evidence summaries for human review. The system never automatically rewrites or deletes generated clusters.

It adds:

- `configs/merge_suggestion_config.yaml`
- `data/processed/cluster_merge_candidates.jsonl`
- `data/processed/cluster_group_reviews.jsonl`
- `data/processed/reviewed_cluster_groups.jsonl`
- `data/quarantine/invalid_merge_candidates.jsonl`
- `data/quarantine/invalid_reviewed_groups.jsonl`
- `outputs/cluster_merge_suggestions.md`
- `outputs/reviewed_cluster_groups_report.md`
- `demand-radar suggest-merges`
- `demand-radar build-merge-report`
- `demand-radar build-reviewed-groups`
- `demand-radar build-reviewed-groups-report`
- `demand-radar run-stage25`

Only human `confirm_merge` reviews create reviewed cluster groups. `reject_merge` and `not_same_demand` are stored as feedback memory but do not create groups. Future truth scoring should prefer `reviewed_cluster_groups.jsonl` when it exists, then fall back to original demand clusters.

## Stage 2.6 Scope

Stage 2.6: Real Signal Expansion & Batch Radar Run.

This layer expands the manual sample set from the original 20 calibration samples to an 80-row batch sample file. The point is not to score opportunities yet; it is to see whether pain extraction, quarantine, clustering, merge suggestions, and reviewed groups remain stable at a more realistic 50-100 signal scale.

It adds:

- `examples/real_signal_samples_stage26.csv`
- `configs/batch_config.yaml`
- `outputs/batch_summary_report.md`
- optional runtime `outputs/batch_quality_matrix.csv`
- `demand-radar run-stage26`
- `demand-radar build-batch-summary`
- Review UI batch filtering across pain calibration, demand cluster review, and merge suggestion review

The Stage 2.6 sample file adds these optional fields:

```text
batch_id
source_note
signal_focus
expected_quality
```

`batch_id` groups samples into reviewable batches such as `batch_stage26_ai_research`, `batch_stage26_content_workflow`, `batch_stage26_agent_workflow`, `batch_stage26_devtools`, `batch_stage26_enterprise_knowledge`, and `batch_stage26_noise`.

`source_note` is a human note about where the excerpt came from, such as `GitHub issue-style excerpt` or `微信群讨论脱敏转述`.

`signal_focus` records why the sample was included: `pain`, `workaround`, `competitor_gap`, `feature_gap`, `weak_signal`, `noise`, `hiring_signal`, or `workflow_repetition`.

`expected_quality` is the human expectation before running extraction: `strong`, `medium`, `weak`, or `noise`.

These fields are analysis dimensions only. They do not overwrite raw state, accepted pain points, generated clusters, merge candidates, or human reviews.


## Stage 2.9 Scope

Stage 2.9: Real LLM Semantic Merge Pilot.

This layer activates the real LLM judge path. Rule-based outputs are preserved unchanged; LLM results go to separate llm_* paths. A comparison report shows how decisions shifted and whether the exception rate improved.

### Why real LLM after rule_based_stub

`rule_based_stub` can only score similarity fields and overlap signals. It cannot understand whether two demand clusters describe the same higher-level workflow. A real LLM can:

- Confirm merges that share a user task but use different words.
- Reject merges that share keywords but serve different workflows.
- Generate clearer demand group titles in Chinese.
- Reduce maybe_merge (human exceptions) by making confident decisions.

### Provider support

- `openai_compatible` — calls `{base_url}/chat/completions` with OpenAI message format.
- `anthropic_compatible` — calls `{base_url}/messages` with Anthropic message format and `x-api-key` header.

### Configure real LLM

Create a local `.env` file (never commit it):

```bash
DEMAND_RADAR_LLM_BASE_URL=https://api.openai.com/v1
DEMAND_RADAR_LLM_API_KEY=sk-...
# Optional: override model from env
DEMAND_RADAR_LLM_MODEL=gpt-4o-mini
```

Then update `configs/semantic_merge_config.yaml`:

```yaml
semantic_merge:
  mode: llm
  llm:
    provider: openai_compatible
    model: gpt-4o-mini
```

### LLM output gate

Every LLM response must pass three gates before being accepted:

1. **Schema Gate** (`llm_output_parser.py`): valid JSON, legal decision, confidence in range, Chinese reason, title/summary when confirming.
2. **Evidence Gate**: built in to prompt rules — no external facts, no forced merges.
3. **Confidence Gate** (`exception_queue.py`): auto_confirm ≥ 0.85, auto_reject ≥ 0.85, else human_exception.

Any failure routes to human_exception without interrupting the pipeline.

### LLM cache

Judgments are cached in `data/cache/llm_semantic_merge_cache.jsonl` (gitignored). Re-running with the same candidates skips the API call. Disable with `batch.cache_enabled: false`.

### Running Stage 2.9

```bash
# 1. Ensure merge candidates exist (run Stage 2.8 first, or pass --input)
demand-radar run-stage28 --input examples/real_signal_samples_stage26.csv

# 2. Set .env, update config mode to llm

# 3. Run Stage 2.9
demand-radar run-stage29 --input examples/real_signal_samples_stage26.csv

# Or test without real API (FakeLLMClient)
demand-radar run-stage29 --input examples/real_signal_samples_stage26.csv --fake-llm
```

Outputs:

```text
data/processed/llm_semantic_merge_judgments.jsonl
data/processed/llm_ai_reviewed_cluster_groups.jsonl
data/processed/llm_human_exception_queue.jsonl
outputs/llm_semantic_merge_judgment_report.md
outputs/llm_ai_reviewed_cluster_groups_report.md
outputs/llm_human_exception_queue_report.md
outputs/llm_semantic_merge_comparison_report.md
```

Rule-based files are never overwritten.

### Comparison report

`outputs/llm_semantic_merge_comparison_report.md` shows:

- Rule-based vs LLM auto_confirm / auto_reject / human_exception counts
- Decision shift matrix (rule × LLM decisions)
- Candidates that moved from maybe to confirm or reject
- LLM failures and low-confidence outputs
- readiness_source: llm if LLM judgments exist, else rule_based

It adds:

- `src/demand_radar/semantic_merge/llm_client.py` (OpenAI + Anthropic + FakeLLM clients)
- `src/demand_radar/semantic_merge/llm_output_parser.py` (robust JSON parser + validator)
- `src/demand_radar/semantic_merge/llm_cache.py` (JSONL-backed cache)
- `src/demand_radar/semantic_merge/llm_judge_runner.py` (LLM runner with cache + fallback)
- `src/demand_radar/semantic_merge/llm_comparison_report.py` (comparison report builder)
- `src/demand_radar/semantic_merge/llm_reports.py` (LLM-specific report wrappers)
- `demand-radar run-stage29` (with `--fake-llm` flag)
- `demand-radar llm-semantic-merge-judge`, `build-llm-ai-reviewed-groups`, `compare-semantic-merge`
- Review UI: LLM合并对比 Tab with judge source switcher
- `prompts/semantic_merge_judge.md` (strengthened Chinese prompt)
- `configs/semantic_merge_config.yaml` (expanded with llm, thresholds.{auto_confirm.confidence}, batch.cache_key_fields, comparison)
- `.env.example` (LLM environment variable examples)
- `.gitignore` updated (data/cache/, llm_*.jsonl ignored)

## Install

```bash
python -m pip install -e .
```

For development:

```bash
python -m pip install -e ".[dev]"
```

## Run

```bash
demand-radar init
demand-radar import --file examples/sample_signals.csv
demand-radar normalize
demand-radar extract-pain
demand-radar build-pain-report
```

One-command Stage 1 run:

```bash
demand-radar run-stage1 --input examples/sample_signals.csv
```

JSONL input is also supported:

```bash
demand-radar run-stage1 --input examples/sample_signals.jsonl
```

Run Stage 1.5 calibration:

```bash
demand-radar run-calibration --input examples/real_signal_samples.csv
```

Add a human calibration review:

```bash
demand-radar calibration-review add --raw-signal-id sig_000001 --pain-point-id pain_000001 --label bad_quote --note "quote matched a complaint word but missed the real pain"
```

False negatives can be recorded without a pain point ID:

```bash
demand-radar calibration-review add --raw-signal-id sig_000009 --label false_negative --note "The source contains a clear pain but rule_based extraction missed it"
```

Rebuild the calibration report:

```bash
demand-radar build-calibration-report
```

Run Stage 2 clustering from existing pain points:

```bash
demand-radar run-stage2
```

Rebuild Stage 2 from the real-signal sample file and then cluster:

```bash
demand-radar run-stage2 --input examples/real_signal_samples.csv
```

You can also run the two cluster steps separately:

```bash
demand-radar run-cluster
demand-radar build-cluster-report
```

Run Stage 2.5 merge suggestions from existing demand clusters:

```bash
demand-radar run-stage25
```

Rebuild Stage 2 and then generate merge suggestions from the real-signal sample file:

```bash
demand-radar run-stage25 --input examples/real_signal_samples.csv
```

You can also run the Stage 2.5 steps separately:

```bash
demand-radar suggest-merges
demand-radar build-merge-report
demand-radar build-reviewed-groups
demand-radar build-reviewed-groups-report
```

Run the Stage 2.6 expanded batch radar pipeline:

```bash
demand-radar run-stage26 --input examples/real_signal_samples_stage26.csv
```

Rebuild only the batch summary report:

```bash
demand-radar build-batch-summary
```

Run the local Review UI:

```bash
demand-radar review-ui --port 8502
```

Open `http://127.0.0.1:8502` after the command starts. The UI reads the current local pipeline files, shows Chinese review tabs for pain extraction, demand clusters, merge suggestions, and batch overview, lets you click review label buttons, and can rebuild `outputs/calibration_report.md`, `outputs/demand_clusters_report.md`, `outputs/cluster_merge_suggestions.md`, `outputs/reviewed_cluster_groups_report.md`, and `outputs/batch_summary_report.md`. The global batch filter applies to the pain, cluster, and merge review tabs.

Fallback Streamlit command:

```bash
python -m streamlit run src/demand_radar/ui/review_app.py --server.address 127.0.0.1 --server.port 8502
```

## CLI Commands

```text
demand-radar init
demand-radar import --file examples/sample_signals.csv
demand-radar normalize
demand-radar extract-pain
demand-radar build-pain-report
demand-radar run-stage1 --input examples/sample_signals.csv
demand-radar run-calibration --input examples/real_signal_samples.csv
demand-radar calibration-review add --raw-signal-id sig_000001 --label good_extraction --note "quote is useful"
demand-radar build-calibration-report
demand-radar run-cluster
demand-radar build-cluster-report
demand-radar run-stage2 --input examples/real_signal_samples.csv
demand-radar suggest-merges
demand-radar build-merge-report
demand-radar build-reviewed-groups
demand-radar build-reviewed-groups-report
demand-radar run-stage25 --input examples/real_signal_samples.csv
demand-radar run-stage26 --input examples/real_signal_samples_stage26.csv
demand-radar build-batch-summary
demand-radar review-ui --port 8502
```

## Input Format

CSV and JSONL imports support these fields:

```text
title
raw_text
url
source_name
source_type
published_at
language
domain_tags
batch_id
source_note
signal_focus
expected_quality
```

Required fields:

```text
title
raw_text
```

Defaults:

```text
source_name = manual_import
source_type = manual
```

`domain_tags` can be comma-separated or semicolon-separated.

The four batch fields are optional and backward compatible. Older CSV files without them still import normally.

## Output Files

```text
data/raw/raw_signals.jsonl
data/processed/normalized_signals.jsonl
data/processed/pain_points.jsonl
data/processed/calibration_reviews.jsonl
data/processed/demand_clusters.jsonl
data/processed/cluster_reviews.jsonl
data/processed/cluster_merge_candidates.jsonl
data/processed/cluster_group_reviews.jsonl
data/processed/reviewed_cluster_groups.jsonl
data/quarantine/invalid_outputs.jsonl
data/quarantine/invalid_clusters.jsonl
data/quarantine/invalid_merge_candidates.jsonl
data/quarantine/invalid_reviewed_groups.jsonl
outputs/pain_points_report.md
outputs/calibration_report.md
outputs/demand_clusters_report.md
outputs/cluster_merge_suggestions.md
outputs/reviewed_cluster_groups_report.md
outputs/batch_summary_report.md
outputs/batch_quality_matrix.csv
outputs/run_summary.json
```

Only pain points that pass State Gate enter `pain_points.jsonl`. Invalid schema, missing evidence, quote mismatch, low confidence, empty text, duplicate signals, and extractor errors go to quarantine.

`calibration_report.md` summarizes human review labels such as `good_extraction`, `weak_extraction`, `false_positive`, `false_negative`, `bad_quote`, `bad_persona`, and `should_quarantine`. These reviews are separate from `pain_points.jsonl`; review labels do not automatically mutate accepted pain points.

The Review UI displays pain points, quarantine items, Chinese demand summaries, Chinese evidence summaries, latest review state, and optional correction fields for expected persona, expected evidence summary, and expected pain description. Visible labels, filters, buttons, warnings, and status messages are Chinese; stored review labels remain the stable schema values such as `good_extraction` and `bad_quote`.

`demand_clusters_report.md` summarizes Stage 2 demand topic candidates. It includes Chinese titles, Chinese summaries, target users, domains, evidence counts, representative pain descriptions, representative evidence summaries, current alternatives, cluster confidence, and review status.

`cluster_reviews.jsonl` stores labels such as `good_cluster`, `too_broad`, `too_narrow`, `wrong_grouping`, `duplicate_cluster`, `bad_title`, `should_merge`, `should_split`, and `not_a_real_demand`. These reviews never rewrite generated clusters.

`cluster_merge_suggestions.md` summarizes candidate pairs that may be mergeable. Each suggestion includes a Chinese reason, similarity score, field-level diagnostics, shared keywords, and representative evidence summaries. Suggestions are candidate state only.

`cluster_group_reviews.jsonl` stores merge review labels such as `confirm_merge`, `reject_merge`, `maybe_merge`, `wrong_reason`, `bad_title`, `needs_split`, `duplicate_candidate`, and `not_same_demand`.

`reviewed_cluster_groups.jsonl` stores only human-confirmed demand groups. It is built from confirmed pairwise reviews using connected components, so `A+B` and `B+C` become one reviewed group `[A, B, C]`. It never overwrites `demand_clusters.jsonl`.

`batch_summary_report.md` summarizes Stage 2.6 batch-level quality and readiness. It includes raw signal counts, pain point counts, quarantine rate, demand clusters, singleton clusters, merge candidates, reviewed groups, calibration review labels, a quality matrix, and a mechanical Stage 3 readiness judgement.

Stage 3 readiness uses fixed rules:

```text
raw_signals >= 50 -> sample_size_ok
pain_points >= 35 -> pain_volume_ok
reviewed_groups >= 5 -> group_volume_ok
singleton_rate <= 0.75 -> clustering_convergence_ok
```

If all four pass, `ready_for_truth_scoring` is `yes`. If two or three pass, it is `partial`. If fewer than two pass, it is `no`.

## Directory Structure

```text
configs/
  domain_config.yaml
  source_registry.yaml
  extraction_config.yaml
  calibration_config.yaml
  clustering_config.yaml
  merge_suggestion_config.yaml
  batch_config.yaml
examples/
  sample_signals.csv
  sample_signals.jsonl
  real_signal_samples.csv
  real_signal_samples_stage26.csv
data/
  raw/
  processed/
  quarantine/
outputs/
  pain_points_report.md
  calibration_report.md
  demand_clusters_report.md
  cluster_merge_suggestions.md
  reviewed_cluster_groups_report.md
  batch_summary_report.md
  run_summary.json
prompts/
  pain_extraction.md
  llm_pain_extraction.md
src/demand_radar/
  cli.py
  calibration/
  clustering/
  ui/
  config/
  intake/
  cleaning/
  state/
  extraction/
  loops/
  reporting/
tests/
```

## Tests

```bash
python -m pytest
```

## Current Limits

- No automated web crawling.
- No Reddit, Hacker News, or GitHub Issues API import.
- No real LLM extraction yet. `LLMExtractorStub` is interface-only and never calls external APIs.
- Real LLM semantic merge (`mode: llm`) requires `DEMAND_RADAR_LLM_BASE_URL`, `DEMAND_RADAR_LLM_API_KEY`, and a model name. Without these, the system falls back to `LLMSemanticMergeJudgeStub` (rule-based behavior). Use `--fake-llm` for offline testing.
- Clustering is lightweight rule-based text similarity only; no embeddings or vector database.
- `rule_based_stub` achieves roughly 47% human exception rate. Real LLM mode is expected to lower this below 40%.
- LLM cache (`data/cache/`) is gitignored; it is local only.
- LLM outputs go to `llm_*` paths; rule_based outputs are never overwritten.
- Confirmed AI merge reviews do not mutate `demand_clusters.jsonl`.
- Batch fields are reporting and filtering dimensions only; they do not change the underlying candidate state.
- No truth score.
- No fit score.
- No Top Demand Candidates report.
- No formal multi-user web app. The Review UI is a local Streamlit app only.


## Stage 2.9C: LLM Semantic Merge Calibration

### Why Calibration Is Needed After Real LLM Pilot

Stage 2.9B showed that a real LLM produces high-quality semantic judgments, but the exception
rate was too high (~95%) because:

1. The LLM tended to output `maybe_merge` for cases where a clear `reject` was warranted.
2. The `auto_reject` threshold (0.85) was the same as `auto_confirm`, ignoring the asymmetric
   risk: rejecting a merge candidate is much safer than incorrectly confirming one.
3. Some candidates had missing `similarity_score` fields that caused LLM call failures.

Stage 2.9C addresses all three issues without changing the original rule_based or 2.9B outputs.

### Why auto_reject Threshold Can Be Lower Than auto_confirm

- `auto_confirm` creates a new AI reviewed group that feeds into Stage 3 scoring.
  A false confirm pollutes the evidence pool, so it must be held to a strict standard (0.82).
- `auto_reject` merely records that two clusters should not merge. A false reject is safer —
  the candidate stays in the exception queue for human review.
  Threshold: **0.75** (Stage 2.9C default).

### Why We Cannot Simply Lower the confirm Threshold to Reduce Exception Rate

Lowering `auto_confirm` to 0.70 would admit weak confirms into the fact layer. The evidence
would be thin, group titles would be speculative, and Stage 3 Truth Scores would be unreliable.
The principle: **AI is the default judge, but low-confidence outputs stay in the exception queue.**

### Candidate Preflight

Before each LLM call, Stage 2.9C runs a preflight check:

- If `similarity_score` is `None` but `field_scores` are available, it computes a repaired score.
- If both are missing, the candidate is written to `data/quarantine/invalid_llm_merge_candidates.jsonl`
  and enters the exception queue without an LLM call.

Preflight results: `data/processed/llm_candidate_preflight_results.jsonl`

### Calibrated LLM Outputs

Stage 2.9C stores its results in separate `calibrated_llm_*` paths:

```
data/processed/calibrated_llm_semantic_merge_judgments.jsonl
data/processed/calibrated_llm_ai_reviewed_cluster_groups.jsonl
data/processed/calibrated_llm_human_exception_queue.jsonl
```

Original `semantic_merge_judgments.jsonl` (rule_based) and `llm_semantic_merge_judgments.jsonl`
(2.9B) are never modified.

### Running Stage 2.9C

```bash
# With fake LLM (no API key needed)
demand-radar run-stage29c --input examples/real_signal_samples_stage26.csv --fake-llm

# With real LLM (configure .env first)
demand-radar run-stage29c --input examples/real_signal_samples_stage26.csv

# Or read from existing processed files
demand-radar run-stage29c
```

### Viewing the Calibration Report

```bash
# Report is generated at:
outputs/llm_semantic_merge_calibration_report.md
```

It shows:
- Confidence distribution per decision type
- Gate outcome breakdown (auto_confirm / auto_reject / human_exception)
- Preflight repair and invalid counts
- Threshold impact analysis
- Representative examples from each category

### Stage 3 Entry Conditions (Calibrated LLM)

```
calibrated_ai_reviewed_groups >= 5
calibrated_human_exception_rate <= 45%
LLM call failures: near zero
```

If `calibrated_ai_reviewed_groups >= 8` and `calibrated_human_exception_rate <= 40%`, the
system marks `ready_for_truth_scoring: yes`. Otherwise it remains `partial`.

### readiness_source Priority

```
calibrated_llm > llm > rule_based
```

Stage 3 readiness is computed from the highest-priority source that has complete outputs.

### UI: calibrated_llm Source

In the Review UI (`demand-radar review-ui`):

- **AI 合并判断 Tab**: Source selector now includes `calibrated_llm (2.9C)`.
- **人工异常队列 Tab**: Source selector defaults to `calibrated_llm` exception queue.
- **LLM合并对比 Tab**: Source selector includes `calibrated_llm` alongside `rule_based` and `llm`.

## Next Stage

After Stage 2.9 runs with a real LLM and `llm_ai_reviewed_groups >= 8`, the next stage can add:

- Truth Scoring Loop using `effective_reviewed_groups` (LLM + human) as the primary group source.
- Fit Scoring Loop.
- Top Demand Candidates report.
- Stronger clustering with embeddings or LLM-assisted labeling if the lightweight method is too noisy.

The core rule remains: no evidence quote, no pain point.


---

## Stage 3: Truth Scoring Loop v1

Stage 3 determines which of the AI-reviewed demand groups look like **real demand**, not just interesting topics.

### What Truth Scoring Is

Truth Scoring answers the question:

> Is this demand group backed by real, repeated, high-confidence evidence?

It scores each reviewed group across 5 dimensions and outputs a `truth_level` (strong / medium / weak / insufficient), a recommended next action, and a full breakdown.

Truth Scoring is **not** Fit Scoring. It does not judge whether you should build a product.

### Why Only Reviewed Groups Are Scored

Singleton clusters, exception queue items, and unreviewed clusters have insufficient convergence evidence. Only groups that passed AI semantic merge (and optionally human review) are scored.

### 5 Scoring Dimensions

| Dimension | Weight | What It Measures |
|---|---:|---|
| Pain Evidence Strength | 30% | Evidence count, specificity, strong negative language |
| Frequency / Repetition | 20% | Cross-source and cross-batch recurrence |
| Existing Workaround | 20% | Manual workarounds, paid tools, internal processes |
| Willingness-to-Pay Signal | 20% | Budget mentions, paid tools, time/business cost signals |
| Persona Clarity | 10% | How clearly the target user is defined |

### Truth Level Classification

| Score | Level |
|---|---|
| 75-100 | strong |
| 55-74 | medium |
| 35-54 | weak |
| 0-34 | insufficient |

Gates override the raw level:
- `evidence_count < 2` → max **weak**
- `source_count <= 1` → adds `single_source_risk`, max **medium**
- `persona_clarity < 40` → adds `unclear_persona`, max **medium**
- `pain_evidence_strength < 40` → adds `weak_pain_evidence`, max **weak**

### Recommended Next Action

| Level | Default Action |
|---|---|
| strong (no severe flags) | `proceed_to_fit_scoring` |
| medium | `needs_more_evidence` |
| weak | `keep_watch` |
| insufficient | `discard` |

### How to Run

```bash
# 1. Ensure Stage 2.9C/D/E outputs exist
demand-radar run-stage28 --input examples/real_signal_samples_stage26.csv
# (run Stage 2.9 with real LLM if calibrated groups are available)

# 2. Run Stage 3 Truth Scoring
demand-radar run-stage3 --source calibrated_llm

# Or step by step:
demand-radar run-truth-scoring --source calibrated_llm
demand-radar build-truth-report
demand-radar build-top-truth-candidates-report
demand-radar build-batch-summary
```

Source options: `calibrated_llm`, `llm`, `ai`, `human`, `auto`, `combined`

### Output Files

```
data/processed/truth_scores.jsonl
data/processed/truth_score_reviews.jsonl   # human feedback (append-only)

outputs/truth_scoring_report.md
outputs/top_truth_candidates_report.md
outputs/batch_summary_report.md            # updated with Stage 3 section
```

### Review UI

```bash
demand-radar review-ui --port 8502
```

A new **真实需求评分** Tab shows:
- Summary metrics (strong / medium / weak / insufficient counts)
- Per-group expandable cards with all dimension scores, signals, risk flags
- 8 human feedback buttons (does not overwrite scores, only appends to reviews file)

### Human Review Notes

Human reviews are written to `truth_score_reviews.jsonl` as append-only feedback. They do **not** modify `truth_scores.jsonl`. The scoring result is always traceable to the rule-based scorer run.

### Stage 4 Readiness

After Stage 3:
- `proceed_to_fit_scoring >= 1` → `ready_for_fit_scoring: yes`
- `medium_or_above >= 2` → `ready_for_fit_scoring: partial`
- Otherwise → `ready_for_fit_scoring: no`

Stage 4 (Fit Scoring) is **not** included in this stage.


---

## Stage 3.2: Evidence Gap Analysis & Targeted Signal Expansion

Stage 3.2 answers: **why are medium candidates not yet strong, and what evidence do we need next?**

### Why Medium Candidates Cannot Enter Fit Scoring Directly

Medium truth scores mean the demand theme looks real, but the evidence is insufficient on at least one key dimension. Entering Fit Scoring prematurely risks evaluating a weakly-supported theme and wasting founder resources.

### Evidence Gap Analysis Goal

For each medium/needs_more_evidence candidate, Stage 3.2 identifies:
- Which scoring dimension is the main bottleneck
- What specific evidence types are missing
- How many new signals to target
- What keywords to search and what source types to prioritize

### Missing Evidence Types

| Type | Meaning |
|---|---|
| `budget_signal` | No budget/pricing/cost context found |
| `paid_alternative` | No paid tool or outsourcing workaround |
| `frequency_signal` | Pain not repeated across multiple posts |
| `source_diversity` | Signals come from too few sources |
| `manual_workaround` | No concrete manual process described |
| `persona_specificity` | Target user role is vague |
| `concrete_pain_quote` | No specific negative-emotion quote |
| `business_impact` | No business loss or missed opportunity described |

### Targeted Signal Collection Plan

Each gap analysis generates a collection plan with:
- Target source types (forum_post, pricing_page, case_study, etc.)
- Chinese and English search keywords
- Positive signal criteria (what counts as good evidence)
- Negative signal criteria (what to reject)

### How to Run

```bash
# Run Stage 3 first if needed
demand-radar run-stage3 --source calibrated_llm

# Run Stage 3.2
demand-radar run-stage32 --source calibrated_llm

# Or step by step
demand-radar analyze-evidence-gaps
demand-radar build-evidence-gap-report
demand-radar build-targeted-signal-plan
```

### Output Files

```
data/processed/evidence_gap_analysis.jsonl
data/processed/targeted_signal_collection_plan.jsonl

outputs/evidence_gap_report.md
outputs/targeted_signal_collection_plan.md
outputs/batch_summary_report.md  (updated with Stage 3.2 section)
```

### Review UI

The **证据缺口分析** Tab in `demand-radar review-ui` shows:
- Summary: candidate count, priority breakdown, total target signals
- Per-candidate cards: bottleneck dimensions, missing evidence types, collection plan keywords

### Next Step

After reviewing the collection plan:
- **Stage 3.3**: Manually or automatically expand signals using the targeted plan
- **Stage 4**: Fit Scoring (only after at least one candidate reaches `strong` level)

---

## Stage 3.3: Targeted Evidence Expansion Run

### Why Not Proceed Directly to Fit Scoring?

After Stage 3.2, medium candidates have clear evidence gaps (missing payment signals, workaround signals, business impact evidence). Rather than entering Fit Scoring with insufficient evidence, Stage 3.3 closes these gaps by generating a targeted collection template and validating new evidence.

### What Stage 3.3 Does

1. Reads the Stage 3.2 `targeted_signal_collection_plan.jsonl` (4 plans × 10 signals = 40 total).
2. Generates `examples/stage33_targeted_signal_template.csv` — pre-populated with correct `evidence_intent`, `target_group_id`, `desired_source_type`, and suggested keywords.
3. You (or an AI assistant) fill in `raw_text`, `url`/`source_note`, and set `collection_status=collected`.
4. Validates filled signals: checks source requirements, payment keyword presence, workaround keyword presence, synthetic flag consistency.
5. Builds `examples/combined_signal_samples_stage33.csv` = original 80 base signals + valid targeted signals.
6. Generates `outputs/targeted_expansion_report.md` and `outputs/truth_score_delta_report.md`.

### Template Generation

```bash
demand-radar build-targeted-signal-template
# outputs: examples/stage33_targeted_signal_template.csv
```

The template has 40 rows (10 per candidate), with `evidence_intent` allocated as:
- `paid_alternative` / `budget_signal` — ≥40% of rows (fill payment/pricing evidence)
- `manual_workaround` / `current_solution` — ≥30% (fill workaround evidence)
- `business_impact` / `time_cost` — ≥20% (fill cost/impact evidence)

### Filling the Template

Edit `examples/real_signal_samples_stage33.csv`:

| Field | Description |
|---|---|
| `raw_text` | Verbatim quote or summary from the source |
| `url` | Source URL (or leave blank and fill `source_note`) |
| `source_note` | E.g., "from internal Slack thread 2026-01-10" |
| `collection_status` | Set to `collected` when done |
| `is_synthetic` | Must be `false` for real evidence |

### What Counts as Valid Evidence

For `evidence_intent=paid_alternative` / `budget_signal`: `raw_text` must contain pricing/cost/subscription keywords (付费, 预算, price, subscription, budget…).

For `evidence_intent=manual_workaround` / `current_solution`: must contain manual/spreadsheet/workaround keywords (人工, 表格, excel, workaround…).

Synthetic signals (`is_synthetic=true`) must have `exclude_from_truth_scoring=true` and are excluded from combined input.

### Validate and Combine

```bash
# Validate your filled signals
demand-radar validate-targeted-signals --input examples/real_signal_samples_stage33.csv

# Build combined input (base + valid targeted)
demand-radar build-combined-stage33-input \
  --base examples/real_signal_samples_stage26.csv \
  --targeted examples/real_signal_samples_stage33.csv
# outputs: examples/combined_signal_samples_stage33.csv
```

### Running Stage 3.3

```bash
# Template-only run (no targeted file required)
demand-radar run-stage33

# After filling examples/real_signal_samples_stage33.csv:
demand-radar run-stage33 --targeted examples/real_signal_samples_stage33.csv
```

### Full Rerun with LLM (requires API key)

```bash
# WARNING: triggers LLM calls
demand-radar run-stage33-full

# Without LLM (for testing)
demand-radar run-stage33-full --skip-llm
```

`run-stage33-full` executes: template → validate → combine → (LLM rerun) → truth scoring → evidence gap analysis → before/after Truth Score delta report.

### Outputs

```
examples/stage33_targeted_signal_template.csv     — 40-row template
examples/real_signal_samples_stage33.csv          — (you fill this)
examples/combined_signal_samples_stage33.csv      — base + validated targeted signals

data/processed/targeted_signal_validation.jsonl   — validation results per signal
data/processed/targeted_expansion_run_summary.json
data/processed/truth_score_deltas.jsonl           — before/after delta per candidate

outputs/targeted_expansion_report.md              — validation summary & issues
outputs/truth_score_delta_report.md               — score improvement per candidate
outputs/batch_summary_report.md                   — updated with Stage 3.3 section
```

### Truth Score Delta Report

After a full rerun, `outputs/truth_score_delta_report.md` shows:
- Before vs. after Truth Score per candidate
- Which dimensions improved
- Which gaps remain
- Whether any candidates reached `strong` / `proceed_to_fit_scoring`

### Review UI

The **定向证据扩展** Tab in `demand-radar review-ui --port 8502` shows:
- Summary metrics: template rows, valid/warning/invalid counts, combined rows
- Per-group coverage: how many signals were collected for each candidate
- Evidence intent distribution
- Validation issue details per group
- Before/after Truth Score comparison cards

### Next Step

After Stage 3.3:
- If any candidate reaches **`strong`** with `proceed_to_fit_scoring` → enter **Stage 4: Fit Scoring**
- If candidates remain `medium` but improved → continue targeted evidence collection
- If no improvement after 2+ rounds → reconsider the need category or persona definition

## Stage 3.4: Candidate Lineage and Targeted Evidence Attribution

After Stage 3.3B adds 40 targeted signals and reruns the full pipeline, the group structure may shift. Stage 3.4 answers: did the score change because of real evidence, or because groups drifted?

Without lineage tracking, a raw before/after delta is unreliable. Stage 3.4 introduces three new artifacts:

1. **Candidate Lineage** - maps each before-candidate to the most likely after-candidate using group ID, title similarity, persona overlap, domain overlap, and targeted-signal overlap.
2. **Targeted Evidence Attribution** - traces each of the 40 targeted signals through raw->pain->cluster->reviewed group, categorising them as attributed_to_expected_group, attributed_to_related_group, lost_in_extraction, lost_in_merge, lost_in_clustering, or excluded_or_invalid.
3. **Stable Truth Score Delta** - combines lineage match strength and attribution evidence to produce a confidence-qualified delta: high (strong match, no drift), medium (weak match or minor drift), or low (split/merged/unmatched or severe drift flags).

**Only high or medium confidence deltas should inform Stage 4 decisions.**

### Why Group Drift Happens

When you add 40 new signals and rerun Stage 2.6 to Stage 3, the LLM may merge, split, or rename groups. A raw title-based delta may compare two groups that are not actually the same object. Candidate Lineage prevents this by computing a weighted match score and flagging drift explicitly.

### Creating a Before-Snapshot

Run this BEFORE expanding signals:

`ash
demand-radar snapshot-truth-state --name before_stage33
`

Saves to: outputs/archive/before_stage33/

If the snapshot was not created before the rerun, Stage 3.4 falls back to data/processed/truth_score_deltas.jsonl and marks lineage_baseline_quality=partial.

### Running Stage 3.4

`ash
# With a before-snapshot:
demand-radar run-stage34 --before-snapshot outputs/archive/before_stage33

# Without a before-snapshot (fallback mode):
demand-radar run-stage34
`

### Understanding delta_confidence

- high: Strong match, no drift flags. Delta is reliable; can inform Stage 4.
- medium: Weak match or minor title drift. Delta is indicative.
- low: Split/merged/unmatched. Do not use for Stage 4 decisions.

### Attribution Rate

The attribution rate = (attributed_to_expected + attributed_to_related) / total targeted signals.

Low attribution (< 50%) means most targeted signals were absorbed into a different group or lost before reaching a reviewed group. Check outputs/targeted_evidence_attribution_report.md for details.

### When to Enter Stage 4

Recommended criteria (all must hold):
1. At least one candidate has after_truth_level = strong
2. That candidate has delta_confidence != low
3. recommended_next_action = proceed_to_fit_scoring

If no candidate meets this bar, continue with another targeted expansion round or run tentative Fit Scoring with clearly marked uncertainty.

### Outputs

`
data/processed/candidate_lineage.jsonl              - per-candidate lineage record
data/processed/targeted_evidence_attribution.jsonl  - per-signal attribution record
data/processed/stable_truth_score_delta.jsonl       - confidence-qualified delta per candidate

outputs/candidate_lineage_report.md                 - match strengths, drift flags, lineage summary
outputs/targeted_evidence_attribution_report.md     - attribution rate by candidate and intent
outputs/stable_truth_score_delta_report.md          - confidence-qualified delta table
outputs/batch_summary_report.md                     - updated with Stage 3.4 block
outputs/archive/before_stage33/                     - (optional) pre-expansion snapshot
`

### Review UI

The candidate lineage tracking tab in demand-radar review-ui --port 8502 shows lineage summary, attribution summary, stable delta summary, and per-candidate cards highlighting low-confidence deltas.

### Example Workflow

`ash
# Step 0: Before expanding signals (IMPORTANT - run before Stage 3.3B)
demand-radar snapshot-truth-state --name before_stage33

# Step 1-2: Fill and validate targeted signals (Stage 3.3)
demand-radar run-stage33
demand-radar run-stage33-full  # triggers LLM

# Step 3: Lineage attribution and stable delta
demand-radar run-stage34 --before-snapshot outputs/archive/before_stage33

# Step 4: Review results in UI
demand-radar review-ui --port 8502
`

## Stage 3.5: Snapshot-First Targeted Evidence Round 2

Stage 3.4 showed that without a proper before-snapshot, delta confidence is only partial.
Stage 3.5 fixes this with a correct experimental posture: snapshot first, then expand
evidence in a narrow, high-priority candidate window.

### Why Not Enter Stage 4 After Stage 3.4?

1. No strong candidate (all medium)
2. No proceed_to_fit_scoring recommendation
3. lineage_baseline_quality=partial (snapshot taken after rerun)
4. attribution_rate only 17.5%

### Candidate Focus

Selects 1-2 candidates matching: AI产业跟踪 / 项目初筛 / 企业知识 / 知识工作流.
Excluded: 内容团队选题, AI Agent工作流可靠性.

### Workflow

```bash
# Step 1: Create before-snapshot BEFORE any evidence expansion
demand-radar snapshot-truth-state --name before_stage35

# Step 2: Generate Stage 3.5 targeted template (24 rows, 2 candidates)
demand-radar run-stage35

# Step 3: Fill examples/real_signal_samples_stage35.csv
# - payment_or_cost_signals >= 60% of rows
# - workaround/current_solution >= 25%
# - raw_text >= 80 characters
# - is_synthetic must be false

# Step 4: Validate and re-run
demand-radar run-stage35

# Step 5: Full LLM rerun + lineage + gate (requires API key)
demand-radar run-stage35-full
```

### Stage 4 Gate

| Status | Conditions |
|---|---|
| pass_formal | strong level + proceed_to_fit_scoring + full baseline + attribution>=50% |
| pass_tentative | after_score>=70 + stable_delta>0 + medium confidence + full baseline |
| blocked | None of the above |

Only pass_formal or pass_tentative allows Stage 4.

### Validation Rules (stricter than Stage 3.3)

- raw_text >= 80 characters
- target_truth_score_id required
- is_synthetic=false enforced
- paid_alternative/budget_signal: payment/cost keywords required (else warning)
- workaround intents: manual/spreadsheet keywords required (else warning)

### Outputs

```
examples/stage35_targeted_signal_template.csv
examples/real_signal_samples_stage35.csv         (you fill this)
examples/combined_signal_samples_stage35.csv
data/processed/stage35_selected_candidates.jsonl
data/processed/stage35_stage4_gate_result.json
outputs/stage35_targeted_expansion_report.md
outputs/stage35_stage4_gate_report.md
outputs/archive/before_stage35/                  (before-snapshot, full quality)
```


---

## Stage R1: Real Evidence Pack & Prompt / Skill Calibration Loop

### Why Stage R1?

Stages 3.x were **pipeline rehearsal** — validating the engineering chain with synthetic and fixture-based samples. Stage R1 marks the switch to **real-world evidence-driven calibration**.

> Fake data + precise scoring ≠ real demand discovery.

Stage R1 is about collecting real, traceable evidence and using it to calibrate the system's extraction prompts, collection skills, rubrics, and rejection rules.

### What is a Real Evidence Pack?

A CSV file where each row represents one piece of real demand evidence for a specific target direction. Every item must:

1. Have a `source_url` (preferred) OR a `source_note` (for interviews/private sources)
2. Have `raw_text` >= 80 characters (real quote or faithful summary — not AI-generated)
3. Identify the `persona` and `workflow_stage`
4. Include at least one signal type: pain, paid alternative, workaround, or business impact

### Trusted Sources (highest to lowest)

| Source Type | Weight | Use For |
|---|---|---|
| product_review | 0.95 | User pain + existing tools |
| community_discussion | 0.90 | Real-world workflow pain |
| github_issue | 0.90 | Technical pain, very precise |
| interview_note | 0.90 | Direct evidence, private |
| case_study | 0.75 | Business impact |
| pricing_page | 0.70 | Paid alternative proof |
| job_posting | 0.70 | Org spending human labor |
| marketing_article | 0.25 | Very low — vendor bias |

### What Gets Rejected

- No `source_url` AND no `source_note` → **invalid**
- `raw_text` < 80 characters → **invalid**
- `is_synthetic=true` without `exclude_from_scoring=true` → **invalid**
- Pure marketing copy without user evidence → **warning or invalid**
- AI-generated content without source → **invalid**

### Quick Start

```bash
# 1. Generate the evidence template
demand-radar build-real-evidence-template

# 2. Fill in examples/real_evidence_pack_ai_investment_tracking.csv
#    with REAL sources (URLs or interview notes)
#    Target: 30-50 items, >= 80% with source_url

# 3. Validate and run
demand-radar run-stage-r1

# 4. Open UI to review and label evidence
demand-radar review-ui --port 8502
```

### Human Calibration Labels

In the UI "真实证据校准" tab, you can label each evidence item:

| Label | Meaning |
|---|---|
| true_pain | Real user pain confirmed |
| fake_pain | Not actually user pain |
| too_generic | Too vague to be useful |
| strong_signal | High quality, use in scoring |
| weak_signal | Low quality, don't rely on it |
| commercial_signal | Clear paid/budget evidence |
| bad_extraction | Extraction prompt got it wrong |
| bad_merge | Merge prompt incorrectly combined |
| missed_pain | Extraction missed a real pain |

Labels write to `data/processed/real_evidence_calibration_reviews.jsonl`.

### Calibration Loop

1. Collect evidence → `examples/real_evidence_pack_ai_investment_tracking.csv`
2. Run pipeline → `demand-radar run-stage-r1`
3. Review system outputs in UI → label items
4. Generate calibration report → `demand-radar build-calibration-report`
5. Read `outputs/prompt_skill_calibration_recommendations.md`
6. Update prompts in `docs/prompts/` and rubrics in `docs/rubrics/`
7. Repeat

### Outputs

```
examples/real_evidence_pack_ai_investment_tracking_template.csv
examples/real_evidence_pack_ai_investment_tracking.csv   (you fill this)
examples/real_evidence_signals_ai_investment_tracking.csv
data/processed/real_evidence_items.jsonl
data/processed/real_evidence_validation.jsonl
data/processed/real_evidence_calibration_reviews.jsonl
outputs/real_evidence_pack_report.md
outputs/real_evidence_calibration_report.md
outputs/prompt_skill_calibration_recommendations.md
docs/skills/real_evidence_collection_skill.md
docs/prompts/pain_extraction_prompt_v1.md
docs/prompts/merge_judgment_prompt_v1.md
docs/rubrics/evidence_scoring_rubric_v1.md
docs/rules/rejection_rules_v1.md
docs/rules/source_weighting_v1.md
```
---

## MVP-A: Automated Acquisition

### Overview

Demand Radar MVP-A integrates `opc-foundation` as the public acquisition layer, upgrading the system from manual evidence input to automated real-signal collection.

```
Domain Config → Source Registry → opc-foundation Connectors → RawSignal → EvidenceCandidate → Evidence Pack Draft → R1 Validation → Reports
```

### opc-foundation Dependency

`opc-foundation` is a separate reusable acquisition library. Install it before using MVP-A:

```bash
# From the parent directory
pip install -e ../opc-foundation
```

The library provides: `HackerNewsConnector`, `GitHubIssuesConnector`, `RssConnector`, `ManualUrlConnector`, `RawSignal`, `SourceRegistry`, `dedupe_raw_signals`.

### Domain Config

`configs/domain_configs/ai_investment_tracking.yaml` — defines target personas, focus workflows, search queries, and quality targets.

### Source Registry

`configs/source_registry_ai_investment_tracking.yaml` — defines enabled sources and connectors.

### Currently Supported Sources

| Source | Connector | API Key? |
|---|---|---|
| Hacker News | `hacker_news` | No (Algolia API) |
| GitHub Issues | `github_issues` | Optional `GITHUB_TOKEN` |
| RSS Feeds | `rss` | No |
| Manual URL CSV | `manual_url` | No |

### Currently NOT Supported

- Reddit, G2, Capterra, App Store, Google Play
- Twitter/X, LinkedIn, 小红书
- Complex crawlers (Playwright/Scrapy)

### Quick Start

```bash
# 1. Run acquisition (fetches real signals from HN, GitHub, RSS)
demand-radar run-acquisition --domain ai_investment_tracking

# 2. Build evidence pack draft CSV
demand-radar build-evidence-pack-draft --domain ai_investment_tracking

# 3. Review draft, fill in persona/pain_type/evidence_quote fields
# Then run R1 validation:
demand-radar validate-real-evidence-pack --input examples/real_evidence_pack_ai_investment_tracking_draft.csv

# 4. Full radar pipeline (acquisition + draft + R1 validation + report)
demand-radar run-radar --domain ai_investment_tracking

# 5. View in UI
demand-radar review-ui --port 8502
```

### Output Files

```
data/raw/acquisition/raw_signals.jsonl
data/processed/acquisition/evidence_candidates.jsonl
data/processed/acquisition/acquisition_run_log.jsonl
examples/real_evidence_pack_ai_investment_tracking_draft.csv
outputs/acquisition/acquisition_report.md
outputs/acquisition/evidence_pack_draft_report.md
outputs/radar/radar_report.md
```
## MVP-B: Domain Relevance Filtering & Pain Extraction

### Overview

MVP-B upgrades the system from "can acquire signals" to "can understand signals."
After MVP-A collects raw evidence candidates via automated acquisition, MVP-B applies:

1. **Domain Relevance Filter** — Filters out off-domain content (e.g. recipe apps, unrelated GitHub repos) using rule-based keyword scoring with optional LLM fallback for uncertain cases.
2. **Pain Extraction** — Uses an LLM to extract structured pain signals from domain-relevant candidates: persona, workflow, pain type, evidence quote, workaround, and commercial signals.
3. **Evidence Pack Filling** — Fills the draft CSV from MVP-A with extracted business fields, making it R1-validator-compatible.
4. **Reports** — Generates domain relevance, pain extraction, top pain signals, and summary reports.

```
evidence_candidates.jsonl (from MVP-A)
        |
        v
Domain Relevance Filter (rule + optional LLM)
        |
        +-- include / uncertain --> Pain Extraction (LLM)
        |                               |
        |                               v
        |                        ExtractedPainItem
        |                               |
        +-- exclude                     |
        |                               v
        +-----> Evidence Pack Filler (fills draft CSV)
                        |
                        v
        R1 Validation (before vs. after comparison)
                        |
                        v
                   Reports
```

### Running MVP-B

```bash
# Full MVP-B pipeline (domain relevance + pain extraction + fill + reports)
demand-radar run-mvp-b --domain ai_investment_tracking

# Or step by step:
demand-radar run-domain-relevance --domain ai_investment_tracking
demand-radar run-pain-extraction --domain ai_investment_tracking
demand-radar fill-evidence-pack --domain ai_investment_tracking
demand-radar build-mvp-b-report --domain ai_investment_tracking
```

With test fake LLM (no API key needed):
```bash
demand-radar run-mvp-b --domain ai_investment_tracking --fake-llm --max-items 20
```

## MVP-D: Seeded Evidence Expansion

MVP-D answers the question after MVP-C review: "these pain signals look real, but can the radar find more supporting evidence around them?"

It does not modify `opc-foundation`, does not add new connectors, does not introduce vector databases or complex clustering, and does not turn weak evidence into product decisions. It only expands from reviewed seeds into more evidence.

Pipeline:

```text
MVP-C pain_signal_reviews
  -> seed_profiles
  -> seeded_query_plan
  -> seeded acquisition with existing connectors
  -> real signal gate
  -> MVP-B domain relevance + pain extraction
  -> seed evidence consolidation
  -> lightweight demand themes
  -> MVP-D reports
```

Run end to end:

```bash
demand-radar run-mvp-d --domain ai_investment_tracking
```

Useful limits for local iteration:

```bash
demand-radar run-mvp-d --domain ai_investment_tracking --max-seeds 5 --max-queries 20 --max-results 10
```

Step-by-step commands:

```bash
demand-radar select-expansion-seeds --domain ai_investment_tracking
demand-radar build-seeded-query-plan --domain ai_investment_tracking
demand-radar run-seeded-acquisition --domain ai_investment_tracking
demand-radar run-expansion-extraction --domain ai_investment_tracking
demand-radar build-demand-themes --domain ai_investment_tracking
demand-radar build-mvp-d-report --domain ai_investment_tracking
```

Outputs:

```text
configs/seeded_expansion_config.yaml
data/processed/mvp_d/seed_profiles.jsonl
data/processed/mvp_d/seeded_query_plan.jsonl
data/processed/mvp_d/expansion_evidence_candidates.jsonl
data/processed/mvp_d/expansion_domain_relevance_scores.jsonl
data/processed/mvp_d/expansion_pain_items.jsonl
data/processed/mvp_d/seed_evidence_consolidation.jsonl
data/processed/mvp_d/consolidated_evidence_themes.jsonl
outputs/mvp_d/seed_selection_report.md
outputs/mvp_d/seeded_query_plan_report.md
outputs/mvp_d/seeded_acquisition_report.md
outputs/mvp_d/real_signal_gate_report.md
outputs/mvp_d/expansion_pain_extraction_report.md
outputs/mvp_d/seed_evidence_consolidation_report.md
outputs/mvp_d/demand_theme_grouping_report.md
outputs/mvp_d/mvp_d_summary_report.md
```

The Review UI includes a read-only `MVP-D 证据扩展` tab showing seeds, query plan, acquisition counts, consolidation status, and lightweight themes:

```bash
demand-radar review-ui --port 8502
```

Without an LLM client, MVP-D still runs and clearly reports `real_llm_run: false`; extraction items become rejects rather than fake production positives.

## MVP-D2: Expansion Diagnostics & Query Calibration

MVP-D2 diagnoses why MVP-D found related candidates but produced no new extracted pain evidence. It does not modify `opc-foundation`, add source connectors, or fake live pilot results. It reads MVP-D outputs, attributes rejected candidates by seed/query/source/raw text quality, scores source usefulness, generates a pain-oriented query plan v2, and either runs a small calibrated pilot or reports `blocked_by_missing_search_provider`.

Run end to end:

```bash
demand-radar run-mvp-d2 --domain ai_investment_tracking
```

Step-by-step commands:

```bash
demand-radar diagnose-expansion-rejects --domain ai_investment_tracking
demand-radar build-calibrated-query-plan --domain ai_investment_tracking
demand-radar run-calibrated-expansion --domain ai_investment_tracking
demand-radar compare-expansion-v1-v2 --domain ai_investment_tracking
demand-radar build-mvp-d2-report --domain ai_investment_tracking
```

Outputs:

```text
configs/expansion_diagnostics_config.yaml
configs/query_calibration_config.yaml
data/processed/mvp_d2/reject_diagnostics.jsonl
data/processed/mvp_d2/source_quality_scores.jsonl
data/processed/mvp_d2/calibrated_query_plan_v2.jsonl
data/processed/mvp_d2/calibrated_expansion_candidates.jsonl
data/processed/mvp_d2/calibrated_expansion_pain_items.jsonl
outputs/mvp_d2/reject_diagnostics_report.md
outputs/mvp_d2/source_quality_report.md
outputs/mvp_d2/calibrated_query_plan_report.md
outputs/mvp_d2/calibrated_expansion_report.md
outputs/mvp_d2/d2_comparison_report.md
outputs/mvp_d2/mvp_d2_summary_report.md
```

Query v2 is intentionally biased toward pain evidence rather than generic product discovery. Examples include `"investment research workflow" "spreadsheet"`, `"portfolio monitoring" "hard to track"`, `"deal sourcing" "manual research"`, and `"VC analyst" "due diligence" "spreadsheet"`.

The Review UI includes a read-only `MVP-D2 诊断校准` tab showing reject diagnostics, source quality recommendations, query v2 examples, calibrated pilot status, and v1/v2 comparison.

### Domain Relevance Filter

Configured in `configs/domain_relevance_config.yaml`.

**Rule scoring:**
- Strong positive keywords (investment research, VC, deal sourcing, etc.): +0.25 each
- Weak positive keywords (research automation, company data, etc.): +0.10 each
- Target workflow keywords (investment research, deal sourcing, etc.): +0.20
- Target persona keywords (investor, vc analyst, etc.): +0.20
- Negative keywords (recipe, meal plan, fitness, game, etc.): -0.40 each
- High-trust source types (community_discussion, github_issue): +0.05

**Thresholds:**
- `>= 0.65` → `include`
- `0.45-0.64` → `uncertain` (LLM called if client configured)
- `< 0.45` → `exclude`

### Pain Extraction

Configured in `configs/pain_extraction_config.yaml`.

For each `include` or `uncertain` candidate with `relevance_score >= 0.45`, the LLM prompt extracts:
- `persona` + `persona_confidence`
- `workflow_stage`
- `job_to_be_done`
- `pain_type`
- `pain_description_zh`
- `evidence_quote` (required — must come from raw_text)
- `current_solution`, `paid_alternative`, `business_impact`
- `time_cost_signal`, `budget_signal`
- `commercial_signal_type`
- `evidence_strength` (strong / medium / weak / reject)
- `confidence`

**Hard rules:**
- `should_extract=True` without `evidence_quote` → auto-reject
- `evidence_strength=strong` requires `persona + workflow_stage + pain_description_zh + evidence_quote`
- LLM failure after 1 retry → reject (pipeline continues)
- Results are cached in `.llm_cache/mvp_b/` — reruns are fast

### Evidence Pack Filling

The filler merges relevance and pain results back into the draft CSV:
- Fills `persona`, `workflow_stage`, `pain_type`, `evidence_quote`, `current_solution`, etc.
- Sets `evidence_type` based on extracted signals
- Sets `exclude_from_scoring=true` for: excluded by domain filter, rejected by pain extraction, synthetic items

### LLM Configuration

MVP-B uses the same LLM client as the rest of Demand Radar:
```bash
DEMAND_RADAR_LLM_BASE_URL=http://127.0.0.1:8787/v1
DEMAND_RADAR_LLM_MODEL=claude-sonnet-4-6
DEMAND_RADAR_LLM_API_KEY=your_key
```

Without LLM configured, the pipeline still runs rule-based domain filtering but produces 0 extracted pain items (all `should_extract=False` with reason "no LLM client configured").

### Output Files

```
data/processed/mvp_b/
  domain_relevance_scores.jsonl    # DomainRelevanceResult for all candidates
  extracted_pain_items.jsonl       # ExtractedPainItem for all candidates
  r1_items.jsonl, r1_validation.jsonl      # R1 validation before
  r1_items_after.jsonl, r1_val_after.jsonl # R1 validation after filling

examples/
  real_evidence_pack_ai_investment_tracking_filled.csv  # MVP-B output

outputs/mvp_b/
  domain_relevance_report.md
  pain_extraction_report.md
  top_pain_signals_report.md
  mvp_b_summary_report.md
```

### MVP-B Acceptance Criteria

| Criterion | Threshold |
|---|---|
| Domain relevance filter runs | required |
| Pain extraction runs | required (LLM or graceful fallback) |
| should_extract_true | >= 10 (with LLM) |
| evidence_strength strong + medium | >= 5 (with LLM) |
| Top pain signals have persona + workflow | required |
| All pipeline errors non-fatal | required |

### UI Tab: MVP-B 痛点抽取

The Streamlit UI includes a read-only MVP-B tab showing:
- Domain relevance include/uncertain/exclude counts
- Pain extraction strong/medium/reject counts
- Top 20 pain signals with expandable detail cards

```bash
demand-radar review-ui --port 8502
```
