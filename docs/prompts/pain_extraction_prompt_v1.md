# Pain Extraction Prompt v1

## Purpose

Extract structured demand signals from real evidence `raw_text`.

This prompt is used to call an LLM to extract pain points from a single evidence item. Output must be grounded in the `raw_text`. No hallucination allowed.

---

## Input Variables

- `raw_text`: The original text fragment (real user quote or summary)
- `source_type`: Type of source (product_review, community_discussion, etc.)
- `persona_hint`: Optional hint about who is speaking

---

## System Instruction

```
You are a demand signal extraction expert. Your job is to extract structured information from real user evidence.

Rules:
1. Only extract what is directly supported by the raw_text.
2. If a field has no evidence in the text, output null — do NOT infer or fabricate.
3. Clearly distinguish between user original words and your inference.
4. Marketing language from vendors should NOT be treated as user pain evidence.
5. If the text is too short, too generic, or has no identifiable user/task/pain, set should_reject=true.
```

---

## Prompt Template

```
Extract demand signals from the following evidence:

Source type: {source_type}
Persona hint: {persona_hint}

--- BEGIN RAW TEXT ---
{raw_text}
--- END RAW TEXT ---

Output a JSON object with these fields:

{
  "persona": "who is the user (investor / analyst / researcher / etc.) or null",
  "workflow_stage": "sourcing | tracking | screening | due_diligence | memo_writing | monitoring | reporting | null",
  "job_to_be_done": "what task were they trying to accomplish, in one sentence or null",
  "pain_description_zh": "Chinese description of the core pain point or null",
  "evidence_quote": "the most compelling 1-2 sentences from the raw_text, direct quote preferred or null",
  "current_solution": "how they currently solve this: tool name, spreadsheet, manual process, or null",
  "paid_alternative": "any paid tool or service mentioned, or null",
  "business_impact": "business consequence of the pain: time lost, opportunities missed, revenue impact, or null",
  "commercial_signal": "paid_tool | budget_mentioned | purchasing_intent | existing_vendor | no_signal",
  "confidence": 0.0 to 1.0,
  "should_reject": true or false,
  "reject_reason": "reason if should_reject=true, else null"
}

Important:
- Do NOT invent details not present in the text.
- If source_type is landing_page or marketing_article, be very conservative.
- Set should_reject=true if: text is too short, purely generic trend commentary, no identifiable user or pain, or pure vendor marketing.
```

---

## Known Failure Modes

- **Hallucinating pain**: Model invents specific pain details not in text → fix: add "Only output what is directly supported" to system prompt
- **False commercial signal**: Model marks `paid_tool` when text only mentions free tools → fix: require explicit price/subscription mention
- **Over-generic extraction**: Model outputs vague "information overload" for any tech article → fix: require specific workflow_stage and persona
- **Wrong persona**: Model assigns "investor" to any finance article → fix: add persona_hint validation step

---

## Output Quality Check

Before using extraction output:
1. Does `evidence_quote` match something actually in `raw_text`?
2. Is `persona` plausible given `source_type`?
3. Is `commercial_signal` backed by `paid_alternative` or `current_solution`?
4. If `confidence < 0.6`, treat as warning-level extraction.