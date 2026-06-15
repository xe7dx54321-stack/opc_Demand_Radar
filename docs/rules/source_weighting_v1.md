# Source Weighting v1

## Purpose

Assign a reliability weight (0.0–1.0) to each source type. Higher weight = more influence on Truth Scoring.

---

## Weight Table

| Source Type              | Weight | Rationale                                                              |
|--------------------------|--------|------------------------------------------------------------------------|
| `product_review`         | 0.95   | Real user describing actual experience with a product                  |
| `community_discussion`   | 0.90   | Real user in their own words, peer context                             |
| `github_issue`           | 0.90   | Developer naming specific technical pain, traceable and precise        |
| `interview_note`         | 0.90   | Direct conversation, highest signal but not public                     |
| `case_study`             | 0.75   | Real outcome described but filtered through vendor narrative           |
| `pricing_page`           | 0.70   | Strong paid alternative signal, but no direct pain evidence            |
| `job_posting`            | 0.70   | Proves org is paying humans to solve this manually                     |
| `product_docs`           | 0.60   | Describes solved use cases but vendor perspective                      |
| `landing_page`           | 0.55   | Some customer language but marketing-optimized                         |
| `newsletter`             | 0.55   | Often practitioner-authored, moderate reliability                      |
| `forum_post`             | 0.55   | Similar to community_discussion but may be older                       |
| `analyst_article`        | 0.50   | Industry insight but aggregated, not direct user voice                 |
| `blog_post`              | 0.45   | Personal perspective, variable quality                                 |
| `social_post`            | 0.40   | Short, context-limited, hard to verify                                 |
| `marketing_article`      | 0.25   | Vendor-controlled narrative, bias risk                                 |
| `unknown`                | 0.30   | Cannot assess reliability without source type                          |

---

## Usage Notes

### Combining Multiple Sources

When multiple items support the same pain point:
- 3+ `strong` sources (weight >= 0.75) → can contribute to `medium` truth level
- 5+ diverse strong sources → can contribute to `strong` truth level
- Marketing-only sources never upgrade truth level regardless of quantity

### Pricing Page Special Case

`pricing_page` (weight 0.70) specifically signals:
- Paid alternatives exist → `paid_alternative` signal
- Market is willing to pay → commercial validation
- Does NOT prove user pain — combine with product reviews

### Job Posting Special Case

`job_posting` (weight 0.70) signals:
- Organization spending human labor on this task
- Clear business investment = demand proxy
- Must include role description that maps to the workflow stage

---

## Calibration Notes

These weights are version 1 defaults. They should be updated based on:
- Human calibration reviews showing which source types produce accurate signals
- Domain-specific reliability patterns (e.g., AI investment research community tends to be more active on Twitter/X than GitHub)
- False positive rates per source type observed in human review