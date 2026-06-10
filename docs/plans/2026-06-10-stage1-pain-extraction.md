# Stage 1 Pain Extraction Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the first stable local pipeline for manual demand signal intake, normalization, evidence-backed pain extraction, quarantine, and pain point reporting.

**Architecture:** Use a Typer CLI over a small Python package. Persist Raw State, Normalized State, Pain Points, and Quarantine as JSONL. Use Pydantic schemas for validation, a replaceable extractor interface, a default rule-based extractor, and a State Gate that prevents evidence-free candidates from entering `pain_points.jsonl`.

**Tech Stack:** Python 3.11+, Typer, Pydantic, PyYAML, JSONL, pytest.

---

### Task 1: Stage 1 Config and Runtime Files

**Files:**
- `configs/domain_config.yaml`
- `configs/source_registry.yaml`
- `configs/extraction_config.yaml`
- `src/demand_radar/cli.py`

**Steps:**
1. Keep domain/source config limited to Stage 1.
2. Add extraction config for mode, minimum confidence, evidence requirement, and max text length.
3. Implement `demand-radar init` to create empty runtime files.
4. Test config loading with `tests/test_config.py`.

### Task 2: Pydantic Schemas and JSONL Stores

**Files:**
- `src/demand_radar/config/schemas.py`
- `src/demand_radar/state/raw_store.py`
- `src/demand_radar/state/processed_store.py`
- `src/demand_radar/state/quarantine_store.py`

**Steps:**
1. Define `RawSignal`, `NormalizedSignal`, `PainPoint`, `QuarantineRecord`, and `RunSummary`.
2. Validate required fields and score ranges with Pydantic.
3. Add JSONL read/write helpers.
4. Ensure Raw State is not overwritten by later stages.

### Task 3: Manual Import

**Files:**
- `src/demand_radar/intake/manual_import.py`
- `tests/test_manual_import.py`

**Steps:**
1. Support CSV and JSONL.
2. Generate `sig_000001` style IDs.
3. Generate `content_hash` from title and raw text.
4. Quarantine empty text, missing title, invalid schema, and duplicate content.
5. Keep importing valid rows when one row fails.

### Task 4: Cleaning and Normalization

**Files:**
- `src/demand_radar/cleaning/text_cleaner.py`
- `tests/test_text_cleaner.py`

**Steps:**
1. Strip basic HTML, markdown links, code blocks, and excess whitespace.
2. Truncate with `max_text_chars`.
3. Preserve `raw_signal_id`, source, title, URL, language, tags, and hash.
4. Quarantine empty normalized text.

### Task 5: Rule-Based Extractor and State Gate

**Files:**
- `src/demand_radar/extraction/base.py`
- `src/demand_radar/extraction/rule_based_extractor.py`
- `src/demand_radar/state/state_gate.py`
- `tests/test_rule_based_extractor.py`
- `tests/test_state_gate.py`

**Steps:**
1. Add extractor protocol for future LLM replacement.
2. Implement keyword-based English and Chinese pain detection.
3. Copy `evidence_quote` from the source sentence.
4. Gate candidates on schema validity, evidence quote presence, quote lookup, and confidence threshold.

### Task 6: Pain Extraction Loop and Report

**Files:**
- `src/demand_radar/loops/pain_extraction_loop.py`
- `src/demand_radar/reporting/pain_points_report.py`
- `tests/test_pain_extraction_loop.py`
- `tests/test_report.py`

**Steps:**
1. Read normalized signals.
2. Build minimal working context per signal.
3. Run extractor.
4. Write valid pain points only.
5. Quarantine invalid candidates without stopping the run.
6. Generate `outputs/pain_points_report.md` and `outputs/run_summary.json`.

### Task 7: End-to-End Verification

**Files:**
- `examples/sample_signals.csv`
- `examples/sample_signals.jsonl`

**Steps:**
1. Add 8-10 sample signals covering English pain, Chinese pain, no-pain text, boundary cases, investment research, content production, AI Agent workflow, and developer tools.
2. Run `python -m pytest`.
3. Run `demand-radar run-stage1 --input examples/sample_signals.csv`.
4. Confirm all required output files exist.
