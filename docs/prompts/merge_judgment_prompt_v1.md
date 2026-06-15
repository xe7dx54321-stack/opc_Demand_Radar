# Merge Judgment Prompt v1

## Purpose

Decide whether two pain points belong to the same demand theme and should be merged into one cluster.

---

## Input Variables

- `pain_point_a`: First pain point (with persona, workflow_stage, pain_description, current_solution)
- `pain_point_b`: Second pain point (same structure)

---

## System Instruction

```
You are a demand clustering expert. Your job is to decide whether two pain points represent the same underlying demand, or are distinct enough to remain separate.

Rules:
1. Same demand = same persona + same workflow stage + same core mechanism + similar current workaround.
2. Related but different = different persona, different stage, different solution shape, or different context.
3. When uncertain, prefer keep_separate — merging is harder to reverse.
4. Do NOT merge just because both mention AI or investment.
```

---

## Prompt Template

```
Given these two pain points:

Pain Point A:
Persona: {a.persona}
Workflow stage: {a.workflow_stage}
Pain: {a.pain_description_zh}
Current solution: {a.current_solution}
Evidence quote: {a.evidence_quote}

Pain Point B:
Persona: {b.persona}
Workflow stage: {b.workflow_stage}
Pain: {b.pain_description_zh}
Current solution: {b.current_solution}
Evidence quote: {b.evidence_quote}

Should these be merged into one demand cluster?

Output JSON:
{
  "decision": "merge | keep_separate | uncertain",
  "reason_zh": "Chinese explanation for decision",
  "shared_workflow": "what workflow they share if merging, else null",
  "key_difference": "key difference if keeping separate, else null",
  "confidence": 0.0 to 1.0
}
```

---

## Merge Criteria

Merge when:
- Persona is similar (both investors, or both researchers)
- Workflow stage is the same (both at sourcing, or both at screening)
- Core pain mechanism is the same (both about information scatter, or both about manual verification)
- Current workaround is similar (both using spreadsheets, or both subscribing to same type of tool)

Keep separate when:
- Different persona types (investor vs. startup founder)
- Different workflow stages (sourcing vs. due_diligence)
- Different solution shape (database subscription vs. API integration)
- One is about missing data, one is about too much data

---

## Known Failure Modes

- **Over-merging**: Two pains about "AI information" get merged even if one is about sourcing and one is about portfolio monitoring → fix: require same workflow_stage
- **Under-merging**: Same pain expressed differently in English and Chinese gets kept separate → fix: add semantic similarity check before prompt