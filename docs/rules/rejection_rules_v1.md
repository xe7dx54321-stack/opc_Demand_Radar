# Rejection Rules v1

## Purpose

Define hard rules for rejecting evidence items before they enter Truth Scoring.

---

## Hard Rejection Rules

Items matching any of these rules must be marked `invalid` and excluded from pipeline:

### Rule 1: No Source

```
source_url IS NULL AND source_note IS NULL → invalid
```

Every evidence item must be traceable to a real source.

### Rule 2: Text Too Short

```
len(raw_text) < 80 → invalid
```

A single sentence is not enough to establish a pain signal.

### Rule 3: Synthetic Without Exclusion

```
is_synthetic = true AND exclude_from_scoring = false → invalid
```

Synthetic test items must never enter real scoring.

### Rule 4: AI-Generated Without Source

```
collector_note contains "AI-generated" AND source_url IS NULL AND source_note IS NULL → invalid
```

LLM-generated content without a real source is not valid evidence.

### Rule 5: Marketing-Only Without Customer Evidence

```
source_type = "marketing_article" AND no evidence_quote from real user → warning
```

Pure vendor marketing (no customer testimonials, no user quotes) → warning or invalid depending on content.

### Rule 6: Missing Persona

```
persona IS NULL → evidence cannot reach "high confidence" tier
```

Without knowing who is speaking, pain cannot be attributed to a validated persona.

### Rule 7: No Pain / Workflow / Solution Signal

```
pain_type IS NULL AND evidence_type IS NULL AND current_solution IS NULL → warning
```

If none of the key demand signal fields are present, the item is likely off-target.

### Rule 8: Trend-Only Without User Scene

```
raw_text contains only trend language ("AI is transforming...", "the future of...") 
AND no specific user, task, or workaround → weak_signal or invalid
```

Trend commentary is not a user pain signal.

---

## Warning Rules (not rejected, but flagged)

These generate `warning` status but allow entry into pipeline with reduced weight:

- `persona_confidence < 0.5`
- `source_type in ("social_post", "blog_post")` — lower reliability
- `published_at` is missing (cannot assess recency)
- `evidence_quote` is empty (harder to verify)

---

## Application

These rules are implemented in `real_evidence_validator.py`. The validator:

1. Applies hard rules → `invalid` / `excluded`
2. Applies warning rules → `warning`
3. Remaining valid items → `valid`

Only `valid` and `warning` items enter the pipeline. `warning` items get reduced source weight.