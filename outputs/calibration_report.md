# Extraction Calibration Report

## Run Summary

- Raw signals: 20
- Normalized signals: 20
- Pain points: 16
- Quarantined items: 4
- Calibration reviews: 0
- Generated at: 2026-06-10T06:29:40Z

## Extraction Quality Overview

- Good extraction: 0
- Weak extraction: 0
- False positive: 0
- False negative: 0
- Bad quote: 0
- Bad persona: 0
- Should quarantine: 0

## Review Breakdown

### bad_pain_description
- count: 0
- examples:
  - None

### bad_persona
- count: 0
- examples:
  - None

### bad_quote
- count: 0
- examples:
  - None

### false_negative
- count: 0
- examples:
  - None

### false_positive
- count: 0
- examples:
  - None

### good_extraction
- count: 0
- examples:
  - None

### missing_payment_signal
- count: 0
- examples:
  - None

### missing_workaround
- count: 0
- examples:
  - None

### should_quarantine
- count: 0
- examples:
  - None

### weak_extraction
- count: 0
- examples:
  - None

## Suggested Rule Improvements

- keyword additions: None yet.
- keyword removals: None yet.
- persona rule improvements: None yet.
- state gate improvements: Keep evidence quote and confidence gates strict.
- LLM extractor requirements: LLM extractor must preserve exact quotes and return empty lists for unsupported pain points.

## Next-Step Readiness

- Ready for LLM extractor: no
- Blocking issues: No human calibration reviews recorded yet.
- Recommended next phase: Add real structured LLM extraction only after reviewing calibration notes.
