# Domain-Bounded Demand Radar

This is an internal demand discovery tool.

Domain-Bounded Demand Radar is a local-first system for collecting manual demand signals, preserving raw evidence, normalizing text, extracting evidence-backed pain points, and quarantining weak or invalid outputs.

Stage 1 focuses on manual signal intake and pain extraction only.

No automated web crawling, clustering, scoring, or MVP generation is included in this stage.

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

## CLI Commands

```text
demand-radar init
demand-radar import --file examples/sample_signals.csv
demand-radar normalize
demand-radar extract-pain
demand-radar build-pain-report
demand-radar run-stage1 --input examples/sample_signals.csv
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
data/quarantine/invalid_outputs.jsonl
outputs/pain_points_report.md
outputs/run_summary.json
```

Only pain points that pass State Gate enter `pain_points.jsonl`. Invalid schema, missing evidence, quote mismatch, low confidence, empty text, duplicate signals, and extractor errors go to quarantine.

## Directory Structure

```text
configs/
  domain_config.yaml
  source_registry.yaml
  extraction_config.yaml
examples/
  sample_signals.csv
  sample_signals.jsonl
data/
  raw/
  processed/
  quarantine/
outputs/
  pain_points_report.md
  run_summary.json
prompts/
  pain_extraction.md
src/demand_radar/
  cli.py
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
- No clustering.
- No truth score.
- No fit score.
- No Top Demand Candidates report.
- No web UI.

## Next Stage

After Stage 1 is stable on 20-50 manual signals, the next stage can add:

- LLM structured extraction behind the existing extractor interface.
- Demand Clustering Loop.
- Truth Scoring Loop.
- Fit Scoring Loop.
- Top Demand Candidates report.

The core rule remains: no evidence quote, no pain point.
