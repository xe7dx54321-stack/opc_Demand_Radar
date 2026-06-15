"""Stage 3.5 Stage 4 Gate evaluation."""
from __future__ import annotations
from demand_radar.stage35.stage35_schema import Stage35GateResult
from demand_radar.stage35.stage35_store import write_gate_result
from demand_radar.state.raw_store import next_ids, utc_now_iso


def evaluate_stage4_gate(
    stable_deltas: list[dict],
    lineage_baseline_quality: str = "partial",
    attribution_rate: float | None = None,
    output_path: str | None = None,
) -> Stage35GateResult:
    gate_id = next_ids("s35gate", [], 1)[0]

    formal_eligible: list[str] = []
    tentative_eligible: list[str] = []
    blocked: list[str] = []

    for delta in stable_deltas:
        title = delta.get("after_group_title_zh") or delta.get("before_group_title_zh") or "unknown"
        after_level = delta.get("after_truth_level", "")
        after_action = delta.get("recommended_next_action", "")
        after_score = float(delta.get("after_truth_score") or 0)
        confidence = delta.get("delta_confidence", "low")
        stable_val = float(delta.get("stable_delta") or 0)

        formal_ok = (
            after_level == "strong"
            and after_action == "proceed_to_fit_scoring"
            and confidence in ("high", "medium")
            and lineage_baseline_quality == "full"
            and (attribution_rate is None or attribution_rate >= 0.50)
        )
        if formal_ok:
            formal_eligible.append(title)
            continue

        tentative_ok = (
            after_score >= 70
            and after_level in ("medium", "strong")
            and stable_val > 0
            and confidence in ("high", "medium")
            and lineage_baseline_quality == "full"
        )
        if tentative_ok:
            tentative_eligible.append(title)
            continue

        blocked.append(title)

    if formal_eligible:
        status = "pass_formal"
        joined = ", ".join(formal_eligible[:2])
        reason = f"{len(formal_eligible)}个候选满足正式 Fit Scoring 门禁"
        next_action = f"进入 Stage 4 正式 Fit Scoring，候选：{joined}"
    elif tentative_eligible:
        status = "pass_tentative"
        joined = ", ".join(tentative_eligible[:2])
        reason = f"{len(tentative_eligible)}个候选满足 tentative Fit Scoring 条件：truth_score>=70 + stable_delta>0"
        next_action = f"可尝试进入 Stage 4 Tentative Fit Scoring，明确标注不确定性，候选：{joined}"
    else:
        status = "blocked"
        parts = []
        if lineage_baseline_quality != "full":
            parts.append(f"lineage_baseline_quality={lineage_baseline_quality}")
        if not stable_deltas:
            parts.append("无 stable delta 数据")
        no_strong = all(d.get("after_truth_level") != "strong" for d in stable_deltas)
        if no_strong:
            parts.append("没有 strong 候选")
        low_score = all(float(d.get("after_truth_score") or 0) < 70 for d in stable_deltas)
        if low_score:
            parts.append("全部候选 after_truth_score < 70")
        if attribution_rate is not None and attribution_rate < 0.50:
            parts.append(f"attribution_rate={attribution_rate:.1%} < 50%")
        reason = "尚不满足进入 Stage 4 的条件: " + "; ".join(parts or ["证据不足"])
        next_action = "继续补充付费/替代方案证据，或考虑放弃该方向"

    result = Stage35GateResult(
        gate_result_id=gate_id,
        status=status,
        reason_zh=reason,
        eligible_candidates=formal_eligible,
        tentative_candidates=tentative_eligible,
        blocked_candidates=blocked,
        required_next_action_zh=next_action,
        created_at=utc_now_iso(),
    )
    write_gate_result(result, path=output_path)
    return result
