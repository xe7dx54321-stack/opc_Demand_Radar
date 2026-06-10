# LLM Pain Extraction Prompt Draft

## Task

Extract concrete, evidence-backed demand pain points from one normalized signal.

Do not infer pain points that are not supported by the text.
Every pain point must include an evidence_quote copied exactly from the input text.
If no concrete pain point exists, return an empty list.

## Input Fields

```json
{
  "raw_signal_id": "sig_000001",
  "normalized_signal_id": "norm_000001",
  "source_name": "manual_import",
  "title": "Signal title",
  "normalized_text": "The text to inspect.",
  "url": "https://example.com",
  "language": "en",
  "domain_tags": ["ai_agent_workflow"]
}
```

## Output JSON Schema

Return a JSON array. Each item must follow this shape:

```json
{
  "persona": "investor | researcher | founder | content_team | fa | strategy_bd | developer | operator | null",
  "scenario": "short scenario or null",
  "job_to_be_done": "short job statement or null",
  "current_workaround": "current workaround or null",
  "pain_description": "non-empty description supported by the text",
  "pain_intensity": 1,
  "frequency_signal": "daily | weekly | monthly | occasional | null",
  "payment_signal": "paid database, subscription, labor cost, budget signal, or null",
  "evidence_quote": "exact substring copied from normalized_text",
  "evidence_span": "same as evidence_quote or a short exact span",
  "confidence": 0.0,
  "extraction_mode": "llm"
}
```

## Rules

- Do not guess persona. Persona can be null.
- Do not invent frequency, payment signal, workaround, or scenario.
- evidence_quote must be an exact substring of normalized_text.
- If evidence_quote is missing or paraphrased, the output will be rejected.
- If the text only announces a launch, feature, benchmark, or generic opinion without a concrete pain, return `[]`.
- Confidence should be 0.65-0.80 for supported but weak signals, and 0.80-0.95 for explicit recurring, costly, or high-intensity pain.

## Positive Example 1

Input:

```json
{
  "normalized_text": "I spend hours every week tracking AI infrastructure companies across blogs, GitHub, filings and newsletters. Paid databases miss many technical updates."
}
```

Output:

```json
[
  {
    "persona": "investor",
    "scenario": "tracking AI infrastructure companies",
    "job_to_be_done": "monitor company and technical updates",
    "current_workaround": "manual tracking across blogs, GitHub, filings and newsletters",
    "pain_description": "AI infrastructure signals are scattered and paid databases miss important technical updates.",
    "pain_intensity": 4,
    "frequency_signal": "weekly",
    "payment_signal": "paid databases miss many technical updates",
    "evidence_quote": "I spend hours every week tracking AI infrastructure companies across blogs, GitHub, filings and newsletters.",
    "evidence_span": "I spend hours every week tracking AI infrastructure companies across blogs, GitHub, filings and newsletters.",
    "confidence": 0.86,
    "extraction_mode": "llm"
  }
]
```

## Positive Example 2

Input:

```json
{
  "normalized_text": "内容团队每天找选题很费时间，公众号、播客、竞品页面的信息太分散，最后还是人工整理到表格里。"
}
```

Output:

```json
[
  {
    "persona": "content_team",
    "scenario": "content topic discovery",
    "job_to_be_done": "find and organize useful topic signals",
    "current_workaround": "manual spreadsheet tracking",
    "pain_description": "内容选题信息分散，人工整理耗时。",
    "pain_intensity": 4,
    "frequency_signal": "daily",
    "payment_signal": "labor/time cost signal mentioned",
    "evidence_quote": "内容团队每天找选题很费时间，公众号、播客、竞品页面的信息太分散，最后还是人工整理到表格里。",
    "evidence_span": "内容团队每天找选题很费时间，公众号、播客、竞品页面的信息太分散，最后还是人工整理到表格里。",
    "confidence": 0.88,
    "extraction_mode": "llm"
  }
]
```

## Negative Example 1

Input:

```json
{
  "normalized_text": "We launched a new dashboard today and added export buttons."
}
```

Output:

```json
[]
```

## Negative Example 2

Input:

```json
{
  "normalized_text": "AI agents will change enterprise software over the next five years."
}
```

Output:

```json
[]
```
