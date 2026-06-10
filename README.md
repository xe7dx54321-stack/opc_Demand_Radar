# Domain-Bounded Demand Radar

This is an internal demand discovery tool.

Domain-Bounded Demand Radar is a local-first system for collecting manual demand signals, preserving raw evidence, normalizing text, extracting evidence-backed pain points, and quarantining weak or invalid outputs.

Stage 1 focuses on manual signal intake and pain extraction only.

No automated web crawling, clustering, scoring, or MVP generation is included in this stage.

Stage 1.5 adds real-signal calibration and LLM extractor readiness. It still does not call a real LLM or external API.

Stage 1.6 adds a local Streamlit Review UI for low-friction calibration review. It is still an internal local tool, not a formal web app.

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

This layer adds a local Streamlit interface for reviewing extracted pain points and quarantined items. It lets a reviewer inspect raw text, normalized text, extraction fields, evidence quote, quarantine reason, and the latest review status in one place.

It adds:

- `demand-radar review-ui`
- `src/demand_radar/ui/review_app.py`
- `src/demand_radar/ui/review_service.py`
- `src/demand_radar/calibration/review_store.py`

The UI writes reviews to `data/processed/calibration_reviews.jsonl`. Reviews are feedback memory only: they do not edit raw signals, normalized signals, quarantine records, or `pain_points.jsonl`.

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

Run the local Review UI:

```bash
demand-radar review-ui
```

The UI reads the current local pipeline files, lets you click a review label button, and can rebuild `outputs/calibration_report.md`.

Fallback Streamlit command:

```bash
python -m streamlit run src/demand_radar/ui/review_app.py
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
demand-radar review-ui
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
data/quarantine/invalid_outputs.jsonl
outputs/pain_points_report.md
outputs/calibration_report.md
outputs/run_summary.json
```

Only pain points that pass State Gate enter `pain_points.jsonl`. Invalid schema, missing evidence, quote mismatch, low confidence, empty text, duplicate signals, and extractor errors go to quarantine.

`calibration_report.md` summarizes human review labels such as `good_extraction`, `weak_extraction`, `false_positive`, `false_negative`, `bad_quote`, `bad_persona`, and `should_quarantine`. These reviews are separate from `pain_points.jsonl`; review labels do not automatically mutate accepted pain points.

The Review UI displays pain points, quarantine items, raw and normalized text, evidence quote highlighting, latest review state, and optional correction fields for expected persona, expected quote, and expected pain description.

## Directory Structure

```text
configs/
  domain_config.yaml
  source_registry.yaml
  extraction_config.yaml
  calibration_config.yaml
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
  run_summary.json
prompts/
  pain_extraction.md
  llm_pain_extraction.md
src/demand_radar/
  cli.py
  calibration/
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
- No clustering.
- No truth score.
- No fit score.
- No Top Demand Candidates report.
- No formal multi-user web app. Stage 1.6 only includes a local Streamlit Review UI.

## Next Stage

After Stage 1 is stable on 20-50 manual signals, the next stage can add:

- LLM structured extraction behind the existing extractor interface.
- Demand Clustering Loop.
- Truth Scoring Loop.
- Fit Scoring Loop.
- Top Demand Candidates report.

The core rule remains: no evidence quote, no pain point.
