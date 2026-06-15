"""Rule-based Truth Scorer for Stage 3 v1.

Scores a reviewed cluster group across 5 dimensions and computes a
weighted Truth Score (0-100).
"""
from __future__ import annotations

import re
from typing import Any

# Keyword lists for signal detection
_WORKAROUND_KEYWORDS = [
    "excel", "spreadsheet", "google sheet", "\u8868\u683c", "\u7535\u5b50\u8868\u683c",
    "\u624b\u5de5", "\u4eba\u5de5", "manual", "\u4eba\u5de5\u6574\u7406", "\u4eba\u5de5\u5904\u7406",
    "\u624b\u52a8", "\u5916\u5305", "\u5185\u90e8\u6d41\u7a0b", "\u811a\u672c",
    "workaround", "\u66ff\u4ee3", "\u66ff\u4ee3\u65b9\u6848", "\u66ff\u4ee3\u54c1",
    "\u5de5\u5177", "tool", "\u4ed8\u8d39\u5de5\u5177", "paid tool",
    "\u6bcf\u5929", "\u6bcf\u5468", "\u6bcf\u6708", "\u5b9a\u671f",
]

_PAYMENT_KEYWORDS = [
    "pay", "paid", "\u4ed8\u8d39", "\u8d2d\u4e70", "\u8ba2\u9605", "\u9a7e\u9a6d\u8d39",
    "budget", "\u9884\u7b97", "cost", "\u6210\u672c", "\u8d39\u7528",
    "\u8d39\u65f6", "\u65f6\u95f4\u6210\u672c", "\u4eba\u529b\u6210\u672c",
    "\u4e1a\u52a1\u635f\u5931", "\u6536\u5165\u5f71\u54cd", "revenue",
    "price", "\u4ef7\u683c", "subscription", "\u6d41\u5931", "\u8fdf\u5ef6",
    "hour", "\u5c0f\u65f6", "\u6bcf\u5929\u82b1", "\u82b1\u8d39",
]

_PAIN_STRONG_KEYWORDS = [
    "\u975e\u5e38", "\u5f88\u9ebb\u70e6", "\u6781\u5ea6\u4e0d\u4fbf", "\u592a\u6162",
    "\u6548\u7387\u5f88\u4f4e", "\u6d49\u70b9", "\u5f71\u54cd\u5de5\u4f5c",
    "\u4e25\u91cd\u95ee\u9898", "\u963b\u788d", "\u65e0\u6cd5", "\u5f88\u96be",
    "extremely", "frustrating", "impossible", "broken", "terrible",
    "\u6d6a\u8d39", "\u8017\u65f6", "\u8017\u8d39", "\u4f4e\u6548",
]

_BARRIER_KEYWORDS = [
    "\u65e0\u6cd5", "\u4e0d\u80fd", "\u5f88\u96be", "\u5f88\u9ebb\u70e6",
    "cannot", "unable", "hard to", "\u963b\u788d", "\u4e2d\u65ad",
]


def score_group(group: dict) -> dict[str, Any]:
    """Compute dimension scores and aggregate Truth Score for a reviewed group.

    Returns a dict with dimension_scores, truth_score, positive_signals,
    negative_signals, risk_flags, scoring_reason_zh, recommended_next_action.
    """
    evidence_count = int(group.get("evidence_count", 0))
    source_count = int(group.get("source_count", 0))
    batch_ids = list(group.get("batch_ids", []))
    personas = list(group.get("personas", []))
    domain_tags = list(group.get("domain_tags", []))
    workarounds = list(group.get("current_workarounds", []))
    quotes = list(group.get("representative_quotes", []))
    pain_descs = list(group.get("representative_pain_descriptions", []))
    group_title = str(group.get("group_title_zh", ""))
    group_summary = str(group.get("group_summary_zh", ""))

    # All text for keyword search
    all_text = " ".join([
        group_title, group_summary,
        " ".join(str(q) for q in quotes),
        " ".join(str(p) for p in pain_descs),
        " ".join(str(w) for w in workarounds),
    ]).lower()

    positive_signals: list[str] = []
    negative_signals: list[str] = []

    # ── 1. Pain Evidence Strength (30%) ──────────────────────────────────
    has_strong_pain = any(kw in all_text for kw in _PAIN_STRONG_KEYWORDS)
    has_barrier = any(kw in all_text for kw in _BARRIER_KEYWORDS)
    pain_desc_len = sum(len(str(p)) for p in pain_descs) + sum(len(str(q)) for q in quotes)
    has_concrete_desc = pain_desc_len > 100

    if evidence_count >= 5 and (has_strong_pain or has_barrier) and has_concrete_desc:
        pain_ev = 90.0
    elif evidence_count >= 5 and has_concrete_desc:
        pain_ev = 78.0
    elif evidence_count >= 3 and (has_strong_pain or has_barrier):
        pain_ev = 70.0
    elif evidence_count >= 3 and has_concrete_desc:
        pain_ev = 62.0
    elif evidence_count >= 2 and has_concrete_desc:
        pain_ev = 52.0
    elif evidence_count >= 2:
        pain_ev = 42.0
    elif evidence_count == 1 and has_concrete_desc:
        pain_ev = 32.0
    else:
        pain_ev = 18.0

    if has_strong_pain:
        positive_signals.append("\u5177\u6709\u660e\u786e\u8d1f\u9762\u60c5\u7eea\u8868\u8fbe\uff08\u9ad8\u5f3a\u5ea6\u75db\u70b9\uff09")
    if has_barrier:
        positive_signals.append("\u63cf\u8ff0\u4e86\u660e\u786e\u4efb\u52a1\u963b\u788d\u6216\u65e0\u6cd5\u5b8c\u6210\u7684\u573a\u666f")
    if not has_concrete_desc:
        negative_signals.append("\u75db\u70b9\u63cf\u8ff0\u8fc7\u4e8e\u6a21\u7cca\uff0c\u7f3a\u5c11\u5177\u4f53\u573a\u666f\u7ec6\u8282")

    # ── 2. Frequency / Repetition (20%) ──────────────────────────────────
    batch_count = len(set(batch_ids))
    unique_sources = source_count

    if unique_sources >= 3 or batch_count >= 3:
        freq = 88.0
        positive_signals.append(f"\u8de8 {unique_sources} \u4e2a\u4fe1\u6e90\u6216 {batch_count} \u4e2a\u6279\u6b21\u91cd\u590d\u51fa\u73b0")
    elif unique_sources >= 2 or batch_count >= 2:
        freq = 68.0
        positive_signals.append(f"\u6765\u81ea {unique_sources} \u4e2a\u4e0d\u540c\u4fe1\u6e90")
    elif evidence_count >= 3:
        freq = 50.0
    elif evidence_count >= 2:
        freq = 35.0
    else:
        freq = 15.0
        negative_signals.append("\u51fa\u73b0\u9891\u7387\u8fc7\u4f4e\uff0c\u8bc1\u636e\u8fc7\u4e8e\u96c6\u4e2d")

    # ── 3. Existing Workaround (20%) ──────────────────────────────────
    has_workaround_kw = any(kw in all_text for kw in _WORKAROUND_KEYWORDS)
    workaround_text = " ".join(str(w) for w in workarounds).lower()
    has_explicit_workaround = bool(workarounds) and len(workaround_text) > 20
    has_paid_workaround = any(kw in workaround_text for kw in ["\u4ed8\u8d39", "pay", "paid", "cost", "\u5de5\u5177"])
    is_generic_workaround = "\u9700\u8981\u8fdb\u4e00\u6b65\u4eba\u5de5\u590d\u6838" in workaround_text or "未标注" in workaround_text

    if has_paid_workaround and not is_generic_workaround:
        wa = 88.0
        positive_signals.append("\u5b58\u5728\u4ed8\u8d39\u66ff\u4ee3\u65b9\u6848\u6216\u4ed8\u8d39\u5de5\u5177\u4f7f\u7528\u8bb0\u5f55")
    elif has_explicit_workaround and has_workaround_kw and not is_generic_workaround:
        wa = 72.0
        positive_signals.append("\u5b58\u5728\u660e\u786e\u7684\u4eba\u5de5/\u5de5\u5177\u66ff\u4ee3\u65b9\u6848")
    elif has_workaround_kw and not is_generic_workaround:
        wa = 52.0
    elif is_generic_workaround or (has_explicit_workaround and is_generic_workaround):
        wa = 28.0
        negative_signals.append("\u66ff\u4ee3\u65b9\u6848\u63cf\u8ff0\u8fc7\u4e8e\u6a21\u7cca\uff0c\u65e0\u5177\u4f53\u6267\u884c\u65b9\u5f0f")
    else:
        wa = 18.0
        negative_signals.append("\u672a\u53d1\u73b0\u660e\u786e\u66ff\u4ee3\u65b9\u6848\u4fe1\u53f7")

    # ── 4. Willingness-to-Pay Signal (20%) ──────────────────────────────
    has_pay_signal = any(kw in all_text for kw in _PAYMENT_KEYWORDS)
    pay_text_hits = sum(1 for kw in _PAYMENT_KEYWORDS if kw in all_text)

    if pay_text_hits >= 4:
        wtp = 80.0
        positive_signals.append("\u5177\u5907\u660e\u786e\u4ed8\u8d39/\u9884\u7b97/\u5de5\u5177\u91c7\u8d2d\u8bb0\u5f55")
    elif pay_text_hits >= 2:
        wtp = 60.0
        positive_signals.append("\u5b58\u5728\u65f6\u95f4\u6210\u672c\u6216\u4eba\u529b\u6210\u672c\u4fe1\u53f7")
    elif has_pay_signal:
        wtp = 40.0
    else:
        wtp = 18.0
        negative_signals.append("\u672a\u53d1\u73b0\u4ed8\u8d39\u610f\u613f\u6216\u6210\u672c\u4fe1\u53f7")

    # ── 5. Persona Clarity (10%) ──────────────────────────────────
    n_personas = len(set(personas))
    if n_personas == 0:
        pc = 15.0
        negative_signals.append("\u76ee\u6807\u7528\u6237\u753b\u50cf\u7f3a\u5931")
    elif n_personas == 1:
        pc = 82.0
        positive_signals.append(f"\u76ee\u6807\u7528\u6237\u660e\u786e\uff1a{personas[0]}")
    elif n_personas == 2:
        pc = 62.0
    else:
        pc = 40.0
        negative_signals.append("\u76ee\u6807\u7528\u6237\u53ef\u80fd\u6df7\u6742\uff08\u591a\u89d2\u8272\uff09")

    # ── Aggregate ──────────────────────────────────────────────────────
    weights = {
        "pain_evidence_strength": 0.30,
        "frequency_repetition": 0.20,
        "existing_workaround": 0.20,
        "willingness_to_pay": 0.20,
        "persona_clarity": 0.10,
    }
    dimension_scores = {
        "pain_evidence_strength": round(pain_ev, 1),
        "frequency_repetition": round(freq, 1),
        "existing_workaround": round(wa, 1),
        "willingness_to_pay": round(wtp, 1),
        "persona_clarity": round(pc, 1),
    }
    raw_score = sum(dimension_scores[d] * w for d, w in weights.items())
    truth_score = round(min(100.0, max(0.0, raw_score)), 2)

    # ── Reason ──────────────────────────────────────────────────────
    reason_parts = []
    if pain_ev >= 70:
        reason_parts.append(f"\u75db\u70b9\u8bc1\u636e\u5f3a\uff08\u8bc1\u636e\u91cf={evidence_count}\uff09")
    elif pain_ev >= 40:
        reason_parts.append(f"\u75db\u70b9\u8bc1\u636e\u4e2d\u7b49\uff08\u8bc1\u636e\u91cf={evidence_count}\uff09")
    else:
        reason_parts.append(f"\u75db\u70b9\u8bc1\u636e\u4e0d\u8db3\uff08\u8bc1\u636e\u91cf={evidence_count}\uff09")

    if freq >= 70:
        reason_parts.append("\u91cd\u590d\u9891\u7387\u9ad8")
    if wa >= 60:
        reason_parts.append("\u5b58\u5728\u660e\u786e\u66ff\u4ee3\u65b9\u6848")
    if wtp >= 55:
        reason_parts.append("\u4ed8\u8d39\u610f\u613f\u4fe1\u53f7\u8f83\u5f3a")
    if pc >= 70:
        reason_parts.append(f"\u76ee\u6807\u7528\u6237\u6e05\u6670\uff08{', '.join(personas)}\uff09")

    if negative_signals:
        reason_parts.append("\u4e3b\u8981\u98ce\u9669: " + "; ".join(negative_signals[:2]))

    scoring_reason_zh = "\u3002".join(reason_parts) + "\u3002" if reason_parts else "\u6839\u636e\u89c4\u5219\u6253\u5206\u3002"

    return {
        "dimension_scores": dimension_scores,
        "truth_score": truth_score,
        "positive_signals": list(dict.fromkeys(positive_signals)),
        "negative_signals": list(dict.fromkeys(negative_signals)),
        "scoring_reason_zh": scoring_reason_zh,
    }
