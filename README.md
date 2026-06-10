# Domain-Bounded Demand Radar

This is an internal demand discovery tool.

Domain-Bounded Demand Radar is a local-first system for collecting manual demand signals, preserving raw evidence, normalizing text, extracting evidence-backed pain points, and quarantining weak or invalid outputs.

Stage 1 focuses on manual signal intake and pain extraction only.

No automated web crawling, clustering, scoring, or MVP generation is included in this stage.

Stage 1.5 adds real-signal calibration and LLM extractor readiness. It still does not call a real LLM or external API.

Stage 1.6 adds a local Streamlit Review UI for low-friction calibration review. The visible interface is Chinese-first for local review work. It is still an internal local tool, not a formal web app.

Stage 2 adds a lightweight Demand Clustering Loop and cluster review workflow. Demand clusters are candidate state only; truth scoring and fit scoring are still out of scope.

Stage 2.5 adds cluster merge suggestions and reviewed cluster groups. Merge suggestions are candidate state only; confirmed reviews generate reviewed groups without mutating `demand_clusters.jsonl`.

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

Run the local Review UI:

```bash
demand-radar review-ui --port 8502
```

Open `http://127.0.0.1:8502` after the command starts. The UI reads the current local pipeline files, shows Chinese review tabs for pain extraction, demand clusters, and merge suggestions, lets you click review label buttons, and can rebuild `outputs/calibration_report.md`, `outputs/demand_clusters_report.md`, `outputs/cluster_merge_suggestions.md`, and `outputs/reviewed_cluster_groups_report.md`.

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

## Directory Structure

```text
configs/
  domain_config.yaml
  source_registry.yaml
  extraction_config.yaml
  calibration_config.yaml
  clustering_config.yaml
  merge_suggestion_config.yaml
examples/
  sample_signals.csv
  sample_signals.jsonl
  real_signal_samples.csv
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
- No real LLM extraction yet.
- LLMExtractorStub is interface-only and never calls external APIs.
- Clustering is lightweight rule-based text similarity only; no embeddings or vector database.
- Merge suggestions are lightweight rule-based diagnostics only; confirmed groups still require human review.
- Confirmed merge reviews do not mutate `demand_clusters.jsonl`.
- No truth score.
- No fit score.
- No Top Demand Candidates report.
- No formal multi-user web app. Stage 1.6 only includes a local Streamlit Review UI.

## Next Stage

After Stage 2.5 is stable on reviewed groups, the next stage can add:

- LLM structured extraction behind the existing extractor interface.
- Stronger clustering with embeddings or LLM-assisted labeling if the lightweight method is too noisy.
- Truth Scoring Loop that prefers reviewed cluster groups.
- Fit Scoring Loop.
- Top Demand Candidates report.

The core rule remains: no evidence quote, no pain point.
