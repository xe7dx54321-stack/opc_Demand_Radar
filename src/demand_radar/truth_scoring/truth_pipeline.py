"""Stage 3 Truth Scoring pipeline: load groups, score, gate, persist."""
from __future__ import annotations

from demand_radar.state.raw_store import next_ids, utc_now_iso
from demand_radar.truth_scoring.truth_gate import apply_truth_gate, compute_truth_level
from demand_radar.truth_scoring.truth_input_loader import (
    load_reviewed_groups,
    resolve_source_type_label,
)
from demand_radar.truth_scoring.truth_schema import TruthScore
from demand_radar.truth_scoring.truth_scorer import score_group
from demand_radar.truth_scoring.truth_store import load_truth_scores, write_truth_scores


def run_truth_scoring(source: str = "calibrated_llm") -> list[TruthScore]:
    """Load reviewed groups, score each, apply gates, persist and return TruthScore list."""
    groups = load_reviewed_groups(source)
    existing = load_truth_scores()
    existing_ids = [s.truth_score_id for s in existing]

    ids = next_ids("truth_score", existing_ids, len(groups))
    scores: list[TruthScore] = []

    for sid, group in zip(ids, groups):
        scored = score_group(group)
        raw_level = compute_truth_level(scored["truth_score"])
        risk_flags: list[str] = []

        gated_level, next_action = apply_truth_gate(
            truth_score=scored["truth_score"],
            raw_level=raw_level,
            evidence_count=int(group.get("evidence_count", 0)),
            source_count=int(group.get("source_count", 0)),
            dimension_scores=scored["dimension_scores"],
            risk_flags=risk_flags,
        )

        ts = TruthScore(
            truth_score_id=sid,
            source_type=resolve_source_type_label(group.get("_source_type", source)),
            source_group_id=group.get("group_id", ""),
            group_title_zh=group.get("group_title_zh", ""),
            group_summary_zh=group.get("group_summary_zh", ""),
            truth_score=scored["truth_score"],
            truth_level=gated_level,
            dimension_scores=scored["dimension_scores"],
            evidence_count=int(group.get("evidence_count", 0)),
            source_count=int(group.get("source_count", 0)),
            personas=list(group.get("personas", [])),
            domain_tags=list(group.get("domain_tags", [])),
            positive_signals=scored.get("positive_signals", []),
            negative_signals=scored.get("negative_signals", []),
            risk_flags=risk_flags,
            scoring_reason_zh=scored.get("scoring_reason_zh", "根据规则打分。"),
            recommended_next_action=next_action,
            created_at=utc_now_iso(),
        )
        scores.append(ts)

    write_truth_scores(scores)
    if len(scores) < 5:
        import warnings
        warnings.warn(
            f"run-stage3: only {len(scores)} groups scored — "
            "below recommended minimum of 5. "
            "Check that calibrated groups are real LLM output, not test stubs.",
            UserWarning, stacklevel=2
        )
    return scores
