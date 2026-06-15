# Evidence Scoring Rubric v1

## Purpose

Classify each piece of evidence into a quality tier to guide how much weight it receives in Truth Scoring.

---

## Tier 1: Strong Evidence

Use when the evidence satisfies 3 or more of these criteria:

1. User explicitly describes a **high-frequency, repeated pain point** ("every week", "daily", "constantly")
2. User explicitly says they currently solve it **manually / with spreadsheets / with a team / via outsourcing**
3. User mentions **paying for a tool**, a subscription, or a budget for this problem
4. User mentions **time cost, human cost, opportunity loss, business delay, or duplicate work**
5. Evidence comes from a **real user quote** (not paraphrased by a vendor)
6. Source type is: `product_review`, `community_discussion`, `github_issue`, `interview_note`, or `case_study`
7. Multiple independent sources describe the **same workflow pain**

**Score contribution: high**

---

## Tier 2: Medium Evidence

Use when the evidence satisfies 1-2 of the above criteria but:

- Has a clear scenario but no cost/budget signal
- Mentions a paid alternative but no user complaint
- Comes from an industry article with user quotes but somewhat paraphrased
- Case study that tells the vendor's story more than the user's pain

**Score contribution: medium**

---

## Tier 3: Weak Evidence

Use when:

- Generic opinions or trend commentary without specific persona/workflow
- "Many investors struggle with..." without attribution
- Only contains product marketing language
- Describes potential pain without direct user evidence
- Source is `blog_post`, `analyst_article`, `newsletter`, or `landing_page`

**Score contribution: low — use only to support other signals, not as primary evidence**

---

## Reject: Not a Valid Evidence Signal

Reject when any of these apply:

1. `raw_text` < 80 characters
2. No identifiable user, task, or pain
3. Pure vendor marketing without customer evidence
4. AI-generated without a traceable source
5. SEO filler content
6. `is_synthetic = true`
7. No `source_url` and no `source_note`
8. Completely off-topic (wrong persona, wrong domain)

**Do NOT include in Truth Scoring**

---

## Special Cases

### Pricing Page

- Tier: Medium (proves paid alternatives exist)
- Cannot prove user pain on its own
- Must be combined with other signals showing people actually buy/use it

### Job Posting

- Tier: Medium-Strong (proves organizational investment)
- "We are hiring an AI research analyst to track the market" = evidence someone is paying humans for this
- Combine with product reviews for stronger signal

### GitHub Issue

- Tier: Strong (developer/technical users naming specific pain)
- Very specific, traceable, real user voice

---

## Rubric Application

When applying this rubric in extraction:
1. Assign a tier to each evidence item
2. Flag items as `strong_evidence`, `medium_evidence`, `weak_evidence`, or `should_reject`
3. Only `strong` and `medium` contribute to Truth Score
4. `weak` items are kept for reference but marked with low weight
5. `rejected` items are excluded from all scoring