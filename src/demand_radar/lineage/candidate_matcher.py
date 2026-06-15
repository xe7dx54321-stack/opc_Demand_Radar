"""Stage 3.4: Match before/after truth candidates via lineage signals."""
from __future__ import annotations
import json
from pathlib import Path
from demand_radar.lineage.lineage_schema import CandidateLineage
from demand_radar.lineage.lineage_schema import TargetedEvidenceAttribution
from demand_radar.state.raw_store import next_ids, utc_now_iso


def _title_similarity(a: str, b: str) -> float:
    """Character-level bigram overlap similarity (handles Chinese)."""
    if not a or not b:
        return 0.0
    a_lower, b_lower = a.lower(), b.lower()
    # Bigrams from both space-split tokens and character sequences
    def bigrams(s: str) -> set:
        tokens = s.split() or list(s)
        bigs: set[str] = set()
        # word bigrams
        for i in range(len(tokens) - 1):
            bigs.add(tokens[i] + tokens[i + 1])
        # character bigrams (for Chinese)
        chars = [c for c in s if not c.isspace()]
        for i in range(len(chars) - 1):
            bigs.add(chars[i] + chars[i + 1])
        # also add individual CJK chars
        for c in s:
            if "一" <= c <= "鿿":
                bigs.add(c)
        return bigs
    ba, bb = bigrams(a_lower), bigrams(b_lower)
    if not ba or not bb:
        return 0.0
    intersection = ba & bb
    union = ba | bb
    return len(intersection) / len(union)


def _set_overlap(a: list, b: list) -> float:
    if not a or not b:
        return 0.0
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def match_candidate_lineage(
    before_scores: list[dict],
    after_scores: list[dict],
    attributions: list[TargetedEvidenceAttribution],
    output_path: str | Path = "data/processed/candidate_lineage.jsonl",
    weights: dict | None = None,
) -> list[CandidateLineage]:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if weights is None:
        weights = {
            "title_similarity": 0.25,
            "persona_overlap": 0.15,
            "domain_overlap": 0.10,
            "targeted_signal_overlap": 0.35,
            "pain_point_overlap": 0.15,
        }

    STRONG_THRESHOLD = 0.75
    WEAK_THRESHOLD = 0.50

    # Build attribution map: target_group_id -> set of after_group_ids that signals reached
    # and before_group_id -> targeted signals
    before_gid_to_signals: dict[str, list[str]] = {}
    after_gid_to_signals: dict[str, list[str]] = {}
    for a in attributions:
        tgid = a.target_group_id or ""
        before_gid_to_signals.setdefault(tgid, []).append(a.target_signal_id)
        for agid in a.reviewed_group_ids:
            after_gid_to_signals.setdefault(agid, []).append(a.target_signal_id)

    # Compute pairwise match scores: before x after
    def score_pair(b: dict, a: dict) -> tuple[float, list[str]]:
        reasons: list[str] = []
        t_sim = _title_similarity(
            b.get("group_title_zh", ""), a.get("group_title_zh", "")
        )
        p_ovl = _set_overlap(b.get("personas", []), a.get("personas", []))
        d_ovl = _set_overlap(b.get("domain_tags", []), a.get("domain_tags", []))

        b_gid = b.get("source_group_id", "")
        a_gid = a.get("source_group_id", "")

        # ID exact match boost (same group survived rerun)
        id_match_bonus = 0.0
        if b_gid and a_gid and b_gid == a_gid:
            id_match_bonus = 0.55  # guarantees at least weak match
            reasons.append(f"group_id 完全匹配 {b_gid}")
            t_sim = max(t_sim, 0.80)

        # Targeted signal overlap: signals that targeted b_gid and reached a_gid
        b_signals = set(before_gid_to_signals.get(b_gid, []))
        a_signals = set(after_gid_to_signals.get(a_gid, []))
        ts_ovl = len(b_signals & a_signals) / max(len(b_signals), 1) if b_signals else 0.0

        pp_ovl = 0.0  # pain point overlap (approximated via domain/persona)

        score = max(
            (
                t_sim * weights["title_similarity"]
                + p_ovl * weights["persona_overlap"]
                + d_ovl * weights["domain_overlap"]
                + ts_ovl * weights["targeted_signal_overlap"]
                + pp_ovl * weights["pain_point_overlap"]
            ),
            id_match_bonus,
        )

        if t_sim > 0.3:
            reasons.append(f"标题相似度 {t_sim:.2f}")
        if p_ovl > 0:
            reasons.append(f"persona 重叠 {p_ovl:.2f}")
        if d_ovl > 0:
            reasons.append(f"domain 重叠 {d_ovl:.2f}")
        if ts_ovl > 0:
            reasons.append(f"定向信号重叠 {ts_ovl:.2f}")

        return score, reasons

    # Match each before to best after
    matched_after: dict[str, str] = {}  # before_gid -> after_gid
    matched_before: dict[str, list[str]] = {}  # after_gid -> [before_gids]
    pair_scores: dict[tuple[str, str], tuple[float, list[str]]] = {}

    for b in before_scores:
        b_gid = b.get("source_group_id", "")
        best_score = 0.0
        best_agid = ""
        best_reasons: list[str] = []
        for a in after_scores:
            a_gid = a.get("source_group_id", "")
            s, reasons = score_pair(b, a)
            pair_scores[(b_gid, a_gid)] = (s, reasons)
            if s > best_score:
                best_score = s
                best_agid = a_gid
                best_reasons = reasons
        matched_after[b_gid] = best_agid if best_score >= WEAK_THRESHOLD else ""
        if best_agid and best_score >= WEAK_THRESHOLD:
            matched_before.setdefault(best_agid, []).append(b_gid)

    # Detect splits and merges
    # split: one before -> multiple after (we take best only, but flag near-ties)
    # merge: multiple before -> same after

    lineages: list[CandidateLineage] = []
    n = len(before_scores) + len(after_scores)
    ids = next_ids("lineage", [], n)
    id_iter = iter(ids)

    processed_before: set[str] = set()

    for b in before_scores:
        b_gid = b.get("source_group_id", "")
        processed_before.add(b_gid)
        best_agid = matched_after.get(b_gid, "")
        best_score, best_reasons = pair_scores.get((b_gid, best_agid), (0.0, []))

        # Find the matching after score object
        after_obj = next((a for a in after_scores if a.get("source_group_id") == best_agid), None)

        # Determine match strength
        if not best_agid:
            strength = "unmatched"
        elif len(matched_before.get(best_agid, [])) > 1:
            strength = "merged"
        else:
            # Check if this before maps to multiple afters near threshold
            near_matches = [
                a_gid for a in after_scores
                for a_gid in [a.get("source_group_id", "")]
                if pair_scores.get((b_gid, a_gid), (0,))[0] >= WEAK_THRESHOLD and a_gid != best_agid
            ]
            if near_matches:
                strength = "split"
            elif best_score >= STRONG_THRESHOLD:
                strength = "strong"
            else:
                strength = "weak"

        # Drift flags
        drift_flags: list[str] = []
        if after_obj and b.get("group_title_zh") and after_obj.get("group_title_zh"):
            t_sim = _title_similarity(b["group_title_zh"], after_obj["group_title_zh"])
            if t_sim < 0.3:
                drift_flags.append("group_title_drift")
        if strength in ("split", "merged"):
            drift_flags.append(f"{strength}_candidate")
        if strength == "unmatched":
            drift_flags.append("no_after_match")

        # Targeted signal tracking
        b_signals = before_gid_to_signals.get(b_gid, [])
        matched_sigs = []
        unmatched_sigs = []
        if after_obj:
            a_gid = after_obj.get("source_group_id", "")
            a_sigs = set(after_gid_to_signals.get(a_gid, []))
            for s in b_signals:
                if s in a_sigs:
                    matched_sigs.append(s)
                else:
                    unmatched_sigs.append(s)
        else:
            unmatched_sigs = list(b_signals)

        # Build lineage summary
        if strength == "strong":
            summary = f"高置信匹配：{b.get('group_title_zh','')[:30]} → {after_obj.get('group_title_zh','')[:30] if after_obj else 'N/A'}"
        elif strength == "weak":
            summary = f"弱匹配（{drift_flags}）：before score={b.get('truth_score')} → after score={after_obj.get('truth_score') if after_obj else 'N/A'}"
        elif strength == "split":
            summary = f"候选分裂：before group 映射到多个 after group，delta 可信度降低"
        elif strength == "merged":
            summary = f"候选合并：多个 before group 映射到同一 after group，delta 可信度降低"
        else:
            summary = f"无法匹配：before candidate {b_gid} 未找到对应 after group"
            drift_flags.append("no_after_match")

        lineages.append(CandidateLineage(
            lineage_id=next(id_iter),
            before_truth_score_id=b.get("truth_score_id"),
            before_group_id=b_gid,
            before_group_title_zh=b.get("group_title_zh"),
            before_truth_score=b.get("truth_score"),
            before_truth_level=b.get("truth_level"),
            before_next_action=b.get("recommended_next_action"),
            after_truth_score_id=after_obj.get("truth_score_id") if after_obj else None,
            after_group_id=best_agid or None,
            after_group_title_zh=after_obj.get("group_title_zh") if after_obj else None,
            after_truth_score=after_obj.get("truth_score") if after_obj else None,
            after_truth_level=after_obj.get("truth_level") if after_obj else None,
            after_next_action=after_obj.get("recommended_next_action") if after_obj else None,
            match_score=round(best_score, 3),
            match_strength=strength,
            match_reasons=best_reasons,
            targeted_signal_ids=b_signals,
            matched_targeted_signal_ids=matched_sigs,
            unmatched_targeted_signal_ids=unmatched_sigs,
            drift_flags=drift_flags,
            lineage_summary_zh=summary,
            created_at=utc_now_iso(),
        ))

    # Handle unmatched after candidates
    matched_after_ids = {v for v in matched_after.values() if v}
    for a in after_scores:
        a_gid = a.get("source_group_id", "")
        if a_gid not in matched_after_ids:
            lineages.append(CandidateLineage(
                lineage_id=next(id_iter),
                after_truth_score_id=a.get("truth_score_id"),
                after_group_id=a_gid,
                after_group_title_zh=a.get("group_title_zh"),
                after_truth_score=a.get("truth_score"),
                after_truth_level=a.get("truth_level"),
                after_next_action=a.get("recommended_next_action"),
                match_score=0.0,
                match_strength="missing_baseline",
                drift_flags=["no_before_baseline"],
                lineage_summary_zh=f"新出现的候选（无 before baseline）：{a.get('group_title_zh','')[:40]}",
                created_at=utc_now_iso(),
            ))

    output_path.write_text(
        "\n".join(l.model_dump_json() for l in lineages) + "\n",
        encoding="utf-8"
    )
    return lineages
