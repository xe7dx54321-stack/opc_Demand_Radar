"""Truth Gate: applies level caps and risk flags after raw scoring."""
from __future__ import annotations

LEVEL_ORDER = ["insufficient", "weak", "medium", "strong"]


def compute_truth_level(truth_score: float) -> str:
    if truth_score >= 75:
        return "strong"
    if truth_score >= 55:
        return "medium"
    if truth_score >= 35:
        return "weak"
    return "insufficient"


def _cap_level(current: str, max_level: str) -> str:
    """Cap current level to at most max_level."""
    ci = LEVEL_ORDER.index(current) if current in LEVEL_ORDER else 0
    mi = LEVEL_ORDER.index(max_level) if max_level in LEVEL_ORDER else 0
    return LEVEL_ORDER[min(ci, mi)]


def apply_truth_gate(
    truth_score: float,
    raw_level: str,
    evidence_count: int,
    source_count: int,
    dimension_scores: dict,
    risk_flags: list,
) -> tuple[str, str]:
    """Apply gate rules and return (gated_level, recommended_next_action).

    risk_flags list is mutated in place to add detected risk flags.
    """
    level = raw_level

    # Gate 1: evidence_count < 2 => max weak
    if evidence_count < 2:
        level = _cap_level(level, "weak")

    # Gate 2: source_count <= 1 => add risk flag, max medium
    if source_count <= 1:
        if "single_source_risk" not in risk_flags:
            risk_flags.append("single_source_risk")
        level = _cap_level(level, "medium")

    # Gate 3: persona_clarity < 40 => add risk flag, max medium
    persona_clarity = dimension_scores.get("persona_clarity", 100.0)
    if persona_clarity < 40:
        if "unclear_persona" not in risk_flags:
            risk_flags.append("unclear_persona")
        level = _cap_level(level, "medium")

    # Gate 4: pain_evidence_strength < 40 => add risk flag, max weak
    pain_ev = dimension_scores.get("pain_evidence_strength", 100.0)
    if pain_ev < 40:
        if "weak_pain_evidence" not in risk_flags:
            risk_flags.append("weak_pain_evidence")
        level = _cap_level(level, "weak")

    # Recommended next action
    next_action = _compute_next_action(level, risk_flags)
    return level, next_action


def _compute_next_action(level: str, risk_flags: list) -> str:
    severe_risks = {"weak_pain_evidence"}
    has_severe = bool(severe_risks & set(risk_flags))

    if level == "strong" and not has_severe:
        return "proceed_to_fit_scoring"
    if level == "medium":
        return "needs_more_evidence"
    if level == "weak":
        return "keep_watch"
    return "discard"
