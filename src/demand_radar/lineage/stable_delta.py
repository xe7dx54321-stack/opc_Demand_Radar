"""Stage 3.4: Compute stable truth score delta with confidence from lineage."""
from __future__ import annotations
from pathlib import Path
from demand_radar.lineage.lineage_schema import CandidateLineage, StableTruthScoreDelta
from demand_radar.state.raw_store import next_ids, utc_now_iso


def compute_stable_deltas(
    lineages: list[CandidateLineage],
    output_path: str | Path = "data/processed/stable_truth_score_delta.jsonl",
) -> list[StableTruthScoreDelta]:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    ids = next_ids("stable_delta", [], len(lineages))
    results: list[StableTruthScoreDelta] = []

    for delta_id, lin in zip(ids, lineages):
        b_score = lin.before_truth_score
        a_score = lin.after_truth_score
        stable_delta = round(a_score - b_score, 2) if (a_score is not None and b_score is not None) else None

        # Determine confidence
        drift = lin.drift_flags
        strength = lin.match_strength

        if strength == "strong" and not drift:
            confidence = "high"
        elif strength in ("strong", "weak") and len([d for d in drift if d not in ("group_title_drift",)]) == 0:
            confidence = "medium"
        elif strength in ("split", "merged", "unmatched", "missing_baseline"):
            confidence = "low"
        elif drift:
            confidence = "medium" if strength == "weak" else "low"
        else:
            confidence = "medium"

        # Improvement dimensions (from lineage match reasons + delta direction)
        improved_dims: list[str] = []
        if stable_delta and stable_delta > 0 and confidence in ("high", "medium"):
            # Approximate: positive delta + willingness evidence from attribution
            if lin.matched_targeted_signal_ids:
                improved_dims.append("targeted_evidence_contribution")
            if strength == "strong":
                improved_dims.append("stable_signal_convergence")

        remaining: list[str] = []
        if a_score and a_score < 75:
            remaining.append("insufficient_evidence_for_strong")
        if not lin.matched_targeted_signal_ids:
            remaining.append("low_targeted_signal_attribution")

        # Recommended next action
        if a_score and a_score >= 75 and confidence != "low" and lin.after_truth_level == "strong":
            action = "proceed_to_fit_scoring"
        elif stable_delta and stable_delta >= 8 and confidence != "low" and a_score and a_score >= 60:
            action = "collect_more_targeted_evidence"
        elif strength in ("split", "merged") or (len(drift) >= 2):
            action = "stabilize_lineage"
        else:
            action = "keep_watch"

        # Interpretation
        if strength == "strong" and stable_delta is not None:
            if stable_delta > 0:
                interp = (
                    f"高置信 lineage 匹配：before {b_score:.1f} → after {a_score:.1f}，"
                    f"delta +{stable_delta:.1f} 来自定向证据（matched_signals={len(lin.matched_targeted_signal_ids)}）"
                )
            elif stable_delta < 0:
                interp = (
                    f"高置信 lineage 匹配：before {b_score:.1f} → after {a_score:.1f}，"
                    f"delta {stable_delta:.1f}，可能为重聚类导致 group 组成变化"
                )
            else:
                interp = f"高置信 lineage 匹配：分数稳定在 {a_score:.1f}"
        elif strength == "weak":
            interp = (
                f"弱匹配（漂移标记: {drift}）：delta 结论可信度中等，"
                f"建议结合 attribution 结果综合判断"
            )
        elif strength in ("split", "merged"):
            interp = (
                f"候选{strength_label(strength)}：before/after group 结构变化，"
                f"delta 不可直接用于 Stage 4 决策，建议先稳定聚类"
            )
        elif strength == "missing_baseline":
            interp = "新出现候选，无 before baseline，delta 不可计算"
        else:
            interp = f"无匹配：before candidate 在 after 结果中无对应 group"

        results.append(StableTruthScoreDelta(
            stable_delta_id=delta_id,
            lineage_id=lin.lineage_id,
            before_group_title_zh=lin.before_group_title_zh,
            after_group_title_zh=lin.after_group_title_zh,
            before_truth_score=b_score,
            after_truth_score=a_score,
            stable_delta=stable_delta,
            before_truth_level=lin.before_truth_level,
            after_truth_level=lin.after_truth_level,
            delta_confidence=confidence,
            improvement_dimensions=improved_dims,
            remaining_gaps=remaining,
            drift_flags=drift,
            interpretation_zh=interp,
            recommended_next_action=action,
            created_at=utc_now_iso(),
        ))

    output_path.write_text(
        "\n".join(r.model_dump_json() for r in results) + "\n",
        encoding="utf-8"
    )
    return results


def strength_label(s: str) -> str:
    return {"split": "分裂", "merged": "合并"}.get(s, s)
