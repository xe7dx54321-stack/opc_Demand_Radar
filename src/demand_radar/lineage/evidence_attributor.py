"""Stage 3.4: Evidence attribution - trace targeted signals through pipeline."""
from __future__ import annotations
import csv
import json
from pathlib import Path
from demand_radar.lineage.lineage_schema import TargetedEvidenceAttribution
from demand_radar.state.raw_store import next_ids, utc_now_iso


def _load_jsonl(path: str | Path) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    result = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                result.append(json.loads(line))
            except Exception:
                pass
    return result


def attribute_targeted_evidence(
    targeted_path: str | Path = "examples/real_signal_samples_stage33.csv",
    raw_path: str | Path = "data/raw/raw_signals.jsonl",
    pain_points_path: str | Path = "data/processed/pain_points.jsonl",
    clusters_path: str | Path = "data/processed/demand_clusters.jsonl",
    reviewed_groups_path: str | Path = "data/processed/calibrated_llm_ai_reviewed_cluster_groups.jsonl",
    truth_scores_path: str | Path = "data/processed/truth_scores.jsonl",
    output_path: str | Path = "data/processed/targeted_evidence_attribution.jsonl",
) -> list[TargetedEvidenceAttribution]:
    targeted_path = Path(targeted_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not targeted_path.exists():
        return []

    # Load targeted signals
    with targeted_path.open(encoding="utf-8-sig", newline="") as f:
        targeted_rows = list(csv.DictReader(f))

    # Build lookup maps
    raw_signals = _load_jsonl(raw_path)
    # url -> raw_signal_id
    url_to_raw_id: dict[str, str] = {}
    raw_id_to_raw: dict[str, dict] = {}
    for r in raw_signals:
        rid = r.get("raw_signal_id", "")
        url = (r.get("url", "") or r.get("metadata", {}).get("url", ""))[:80]
        if url:
            url_to_raw_id[url] = rid
        raw_id_to_raw[rid] = r

    # raw_signal_id -> pain_point_ids
    raw_to_pp: dict[str, list[str]] = {}
    for p in _load_jsonl(pain_points_path):
        rid = p.get("raw_signal_id", "")
        raw_to_pp.setdefault(rid, []).append(p["pain_point_id"])

    # pain_point_id -> cluster_ids
    pp_to_clusters: dict[str, list[str]] = {}
    for c in _load_jsonl(clusters_path):
        for ppid in c.get("related_pain_point_ids", []):
            pp_to_clusters.setdefault(ppid, []).append(c["cluster_id"])

    # cluster_id -> group_id
    cluster_to_group: dict[str, str] = {}
    group_id_to_group: dict[str, dict] = {}
    for g in _load_jsonl(reviewed_groups_path):
        gid = g["group_id"]
        group_id_to_group[gid] = g
        for cid in g.get("cluster_ids", []):
            cluster_to_group[cid] = gid

    # group_id -> truth_score_id
    group_to_ts: dict[str, str] = {}
    for ts in _load_jsonl(truth_scores_path):
        group_to_ts[ts["source_group_id"]] = ts["truth_score_id"]

    ids = next_ids("attribution", [], len(targeted_rows))
    attributions: list[TargetedEvidenceAttribution] = []

    for attr_id, row in zip(ids, targeted_rows):
        sig_id = row.get("target_signal_id", "")
        target_gid = row.get("target_group_id", "")
        target_ts_id = row.get("target_truth_score_id", "")
        target_title = row.get("target_group_title_zh", "")
        intent = row.get("evidence_intent", "")
        url = (row.get("url", "") or "")[:80]

        # collection_status check
        if row.get("collection_status", "pending") != "collected":
            attributions.append(TargetedEvidenceAttribution(
                attribution_id=attr_id,
                target_signal_id=sig_id,
                target_group_id=target_gid,
                target_truth_score_id=target_ts_id,
                target_group_title_zh=target_title,
                evidence_intent=intent,
                attribution_status="not_used",
                attribution_confidence=0.0,
                attribution_reason_zh="信号未标记为 collected 状态",
                created_at=utc_now_iso(),
            ))
            continue

        if row.get("is_synthetic", "").lower() in ("true", "1", "yes"):
            attributions.append(TargetedEvidenceAttribution(
                attribution_id=attr_id,
                target_signal_id=sig_id,
                target_group_id=target_gid,
                target_truth_score_id=target_ts_id,
                target_group_title_zh=target_title,
                evidence_intent=intent,
                attribution_status="excluded_or_invalid",
                attribution_confidence=0.0,
                attribution_reason_zh="is_synthetic=true，已排除",
                created_at=utc_now_iso(),
            ))
            continue

        # Trace: url -> raw_signal_id
        raw_id = url_to_raw_id.get(url, "")
        if not raw_id:
            attributions.append(TargetedEvidenceAttribution(
                attribution_id=attr_id,
                target_signal_id=sig_id,
                target_group_id=target_gid,
                target_truth_score_id=target_ts_id,
                target_group_title_zh=target_title,
                evidence_intent=intent,
                raw_signal_id=None,
                attribution_status="lost_in_extraction",
                attribution_confidence=0.1,
                attribution_reason_zh=f"未在 raw_signals 中找到对应 URL，信号可能未通过导入或被去重",
                created_at=utc_now_iso(),
            ))
            continue

        # Trace: raw -> pain_points
        pp_ids = raw_to_pp.get(raw_id, [])
        if not pp_ids:
            attributions.append(TargetedEvidenceAttribution(
                attribution_id=attr_id,
                target_signal_id=sig_id,
                target_group_id=target_gid,
                target_truth_score_id=target_ts_id,
                target_group_title_zh=target_title,
                evidence_intent=intent,
                raw_signal_id=raw_id,
                attribution_status="lost_in_extraction",
                attribution_confidence=0.2,
                attribution_reason_zh=f"raw_signal {raw_id} 未生成任何 pain_point（被抽取过滤或进入 quarantine）",
                created_at=utc_now_iso(),
            ))
            continue

        # Trace: pain_points -> clusters
        cluster_ids: list[str] = []
        for ppid in pp_ids:
            cluster_ids.extend(pp_to_clusters.get(ppid, []))
        cluster_ids = list(set(cluster_ids))
        if not cluster_ids:
            attributions.append(TargetedEvidenceAttribution(
                attribution_id=attr_id,
                target_signal_id=sig_id,
                target_group_id=target_gid,
                target_truth_score_id=target_ts_id,
                target_group_title_zh=target_title,
                evidence_intent=intent,
                raw_signal_id=raw_id,
                pain_point_id=pp_ids[0] if pp_ids else None,
                attribution_status="lost_in_clustering",
                attribution_confidence=0.3,
                attribution_reason_zh=f"pain_point 存在但未进入任何 demand cluster（被 singleton 过滤）",
                created_at=utc_now_iso(),
            ))
            continue

        # Trace: clusters -> reviewed groups
        group_ids: set[str] = set()
        for cid in cluster_ids:
            gid = cluster_to_group.get(cid)
            if gid:
                group_ids.add(gid)

        ts_ids = [group_to_ts[gid] for gid in group_ids if gid in group_to_ts]

        if not group_ids:
            attributions.append(TargetedEvidenceAttribution(
                attribution_id=attr_id,
                target_signal_id=sig_id,
                target_group_id=target_gid,
                target_truth_score_id=target_ts_id,
                target_group_title_zh=target_title,
                evidence_intent=intent,
                raw_signal_id=raw_id,
                pain_point_id=pp_ids[0] if pp_ids else None,
                demand_cluster_ids=cluster_ids,
                attribution_status="lost_in_merge",
                attribution_confidence=0.4,
                attribution_reason_zh=(
                    f"进入 cluster {cluster_ids[:2]} 但未被 LLM 合并入任何 reviewed group"
                ),
                created_at=utc_now_iso(),
            ))
            continue

        # Determine if reached expected group
        if target_gid in group_ids:
            status = "attributed_to_expected_group"
            confidence = 0.9
            reason = f"signal 经路径追踪最终进入预期 group {target_gid}"
        else:
            status = "attributed_to_related_group"
            confidence = 0.6
            actual_groups = list(group_ids)
            reason = f"signal 进入相关 group {actual_groups[:2]}，而非预期 group {target_gid}"

        attributions.append(TargetedEvidenceAttribution(
            attribution_id=attr_id,
            target_signal_id=sig_id,
            target_group_id=target_gid,
            target_truth_score_id=target_ts_id,
            target_group_title_zh=target_title,
            evidence_intent=intent,
            raw_signal_id=raw_id,
            pain_point_id=pp_ids[0] if pp_ids else None,
            demand_cluster_ids=cluster_ids,
            reviewed_group_ids=list(group_ids),
            truth_score_ids=ts_ids,
            attribution_status=status,
            attribution_confidence=confidence,
            attribution_reason_zh=reason,
            created_at=utc_now_iso(),
        ))

    # Write output
    output_path.write_text(
        "\n".join(a.model_dump_json() for a in attributions) + "\n",
        encoding="utf-8"
    )
    return attributions
