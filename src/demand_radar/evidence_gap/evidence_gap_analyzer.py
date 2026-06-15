"""Rule-based Evidence Gap Analyzer for Stage 3.2."""
from __future__ import annotations
from typing import Any
from demand_radar.evidence_gap.evidence_gap_schema import EvidenceGapAnalysis
from demand_radar.state.raw_store import next_ids, utc_now_iso

# Dimension gap thresholds
DIM_TARGETS = {
    "pain_evidence_strength": 65,
    "frequency_repetition": 60,
    "existing_workaround": 55,
    "willingness_to_pay": 50,
    "persona_clarity": 60,
}

# Map low dimension -> missing evidence types
DIM_TO_MISSING: dict[str, list[str]] = {
    "pain_evidence_strength": ["concrete_pain_quote", "stronger_pain_evidence"],
    "frequency_repetition":   ["frequency_signal", "repeated_workflow", "source_diversity"],
    "existing_workaround":    ["manual_workaround", "paid_alternative", "current_solution"],
    "willingness_to_pay":     ["budget_signal", "paid_alternative", "business_impact", "time_cost"],
    "persona_clarity":        ["persona_specificity", "target_role_clarity"],
}


def analyze_gaps(
    truth_scores: list[dict],
    include_weak: bool = False,
) -> list[EvidenceGapAnalysis]:
    """Analyze evidence gaps for medium/strong truth candidates."""
    results: list[EvidenceGapAnalysis] = []
    existing_ids: list[str] = []

    eligible = []
    for s in truth_scores:
        level = s.get("truth_level", "")
        action = s.get("recommended_next_action", "")
        if level in ("strong", "medium"):
            eligible.append(s)
        elif include_weak and level == "weak":
            eligible.append(s)

    ids = next_ids("evidence_gap", existing_ids, len(eligible))

    for gap_id, ts in zip(ids, eligible):
        dim_scores = ts.get("dimension_scores", {})
        bottlenecks = []
        missing: list[str] = []

        for dim, threshold in DIM_TARGETS.items():
            score = dim_scores.get(dim, 100.0)
            if score < threshold:
                bottlenecks.append(dim)
                for ev_type in DIM_TO_MISSING.get(dim, []):
                    if ev_type not in missing:
                        missing.append(ev_type)

        # Ensure at least one missing type
        if not missing:
            missing = ["source_diversity"]

        # Bottleneck label
        if not bottlenecks:
            bottlenecks = ["frequency_repetition"]

        # Priority
        score_val = float(ts.get("truth_score", 0))
        ev_count = int(ts.get("evidence_count", 0))
        wtp = dim_scores.get("willingness_to_pay", 100.0)
        other_ok = all(
            dim_scores.get(d, 100) >= DIM_TARGETS[d]
            for d in DIM_TARGETS if d != "willingness_to_pay"
        )
        if score_val >= 60 and (75 - score_val) <= 15:
            priority = "high"
        elif score_val >= 55:
            priority = "medium"
        else:
            priority = "low"
        # Boost if wtp is main bottleneck but others are ok
        if "willingness_to_pay" in bottlenecks and other_ok and priority == "medium":
            priority = "high"
        # Cap if very few evidence
        if ev_count < 3 and priority == "high":
            priority = "medium"

        # Target new signals
        n_missing_types = len(missing)
        if n_missing_types <= 2:
            target_signals = 4
        elif n_missing_types <= 3:
            target_signals = 6
        elif n_missing_types <= 4:
            target_signals = 8
        else:
            target_signals = 10

        # Gap reason & upgrade path (in Chinese)
        bottleneck_labels = {
            "pain_evidence_strength": "\u75db\u70b9\u8bc1\u636e\u5f3a\u5ea6",
            "frequency_repetition": "\u91cd\u590d\u9891\u7387",
            "existing_workaround": "\u5df2\u6709\u66ff\u4ee3\u65b9\u6848",
            "willingness_to_pay": "\u4ed8\u8d39\u610f\u613f\u4fe1\u53f7",
            "persona_clarity": "\u7528\u6237\u753b\u50cf\u6e05\u6670\u5ea6",
        }
        bottleneck_zh = "\u3001".join(bottleneck_labels.get(b, b) for b in bottlenecks[:3])
        missing_zh_map = {
            "concrete_pain_quote": "\u5177\u4f53\u75db\u70b9\u539f\u8a00",
            "stronger_pain_evidence": "\u66f4\u5f3a\u75db\u70b9\u8bc1\u636e",
            "frequency_signal": "\u91cd\u590d\u9891\u7387\u4fe1\u53f7",
            "repeated_workflow": "\u91cd\u590d\u5de5\u4f5c\u6d41\u8bc1\u636e",
            "source_diversity": "\u6765\u6e90\u591a\u6837\u6027",
            "manual_workaround": "\u4eba\u5de5\u66ff\u4ee3\u65b9\u6848",
            "paid_alternative": "\u4ed8\u8d39\u66ff\u4ee3\u65b9\u6848",
            "current_solution": "\u5f53\u524d\u89e3\u51b3\u65b9\u6848",
            "budget_signal": "\u9884\u7b97/\u6210\u672c\u4fe1\u53f7",
            "business_impact": "\u4e1a\u52a1\u5f71\u54cd\u8bc1\u636e",
            "time_cost": "\u65f6\u95f4\u6210\u672c\u4fe1\u53f7",
            "persona_specificity": "\u7528\u6237\u89d2\u8272\u5177\u4f53\u4fe1\u606f",
            "target_role_clarity": "\u76ee\u6807\u89d2\u8272\u660e\u786e\u5ea6",
            "urgency_signal": "\u7d27\u8feb\u6027\u4fe1\u53f7",
        }
        missing_zh = "\u3001".join(missing_zh_map.get(m, m) for m in missing[:4])
        gap_reason = (
            f"\u5f53\u524d\u5f97\u5206 {score_val:.1f}\uff0c\u4e3b\u8981\u77ed\u677f\u662f\uff1a{bottleneck_zh}\u3002"
            f"\u7f3a\u5c11\uff1a{missing_zh}\u3002"
        )
        upgrade_path = (
            f"\u5efa\u8bae\u8865\u5145 {target_signals} \u6761\u65b0\u4fe1\u53f7\uff0c"
            f"\u91cd\u70b9\u6765\u6e90\uff1a{', '.join(_get_source_types(missing)[:3])}\u3002"
            f"\u9700\u660e\u786e\u4f53\u73b0\uff1a{missing_zh}\u3002"
        )

        gap = EvidenceGapAnalysis(
            gap_analysis_id=gap_id,
            truth_score_id=ts.get("truth_score_id", ""),
            source_group_id=ts.get("source_group_id", ""),
            group_title_zh=ts.get("group_title_zh", ""),
            current_truth_score=score_val,
            current_truth_level=ts.get("truth_level", ""),
            current_next_action=ts.get("recommended_next_action", ""),
            dimension_scores=dim_scores,
            missing_evidence_types=missing,
            main_bottleneck_dimensions=bottlenecks,
            gap_reason_zh=gap_reason,
            upgrade_path_zh=upgrade_path,
            target_new_signals=target_signals,
            priority=priority,
            created_at=utc_now_iso(),
        )
        results.append(gap)

    return results


def _get_source_types(missing: list[str]) -> list[str]:
    source_map: dict[str, list[str]] = {
        "budget_signal": ["pricing_page", "product_review", "case_study"],
        "paid_alternative": ["pricing_page", "product_review", "landing_page"],
        "business_impact": ["case_study", "job_posting", "landing_page"],
        "time_cost": ["case_study", "community_discussion", "forum_post"],
        "frequency_signal": ["forum_post", "community_discussion", "github_issue"],
        "repeated_workflow": ["forum_post", "interview_note", "community_discussion"],
        "source_diversity": ["forum_post", "github_issue", "community_discussion"],
        "manual_workaround": ["product_review", "forum_post", "case_study"],
        "current_solution": ["product_review", "community_discussion"],
        "concrete_pain_quote": ["forum_post", "community_discussion", "interview_note"],
        "stronger_pain_evidence": ["forum_post", "interview_note", "github_issue"],
        "persona_specificity": ["job_posting", "interview_note", "community_discussion"],
        "target_role_clarity": ["job_posting", "interview_note"],
        "urgency_signal": ["forum_post", "community_discussion"],
    }
    sources: list[str] = []
    for m in missing:
        for s in source_map.get(m, []):
            if s not in sources:
                sources.append(s)
    return sources or ["forum_post", "community_discussion"]
