"""Build batch-level summaries across the radar pipeline."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from demand_radar.batch.batch_schema import BatchSummary, BatchSummaryResult, Stage3Readiness
from demand_radar.calibration.review_store import load_reviews
from demand_radar.clustering.cluster_store import load_cluster_reviews, load_demand_clusters
from demand_radar.clustering.merge_store import (
    load_cluster_group_reviews,
    load_merge_candidates,
    load_reviewed_cluster_groups,
)
from demand_radar.config.schemas import QuarantineRecord
from demand_radar.state.processed_store import load_normalized_signals, load_pain_points
from demand_radar.state.quarantine_store import load_quarantine
from demand_radar.state.raw_store import load_raw_signals, utc_now_iso


DEFAULT_BATCH_ID = "default"


def build_batch_summary(
    raw_path: str | Path = "data/raw/raw_signals.jsonl",
    normalized_path: str | Path = "data/processed/normalized_signals.jsonl",
    pain_points_path: str | Path = "data/processed/pain_points.jsonl",
    quarantine_path: str | Path = "data/quarantine/invalid_outputs.jsonl",
    calibration_reviews_path: str | Path = "data/processed/calibration_reviews.jsonl",
    clusters_path: str | Path = "data/processed/demand_clusters.jsonl",
    cluster_reviews_path: str | Path = "data/processed/cluster_reviews.jsonl",
    merge_candidates_path: str | Path = "data/processed/cluster_merge_candidates.jsonl",
    merge_reviews_path: str | Path = "data/processed/cluster_group_reviews.jsonl",
    reviewed_groups_path: str | Path = "data/processed/reviewed_cluster_groups.jsonl",
) -> BatchSummaryResult:
    raw_signals = load_raw_signals(raw_path)
    normalized_signals = load_normalized_signals(normalized_path)
    pain_points = load_pain_points(pain_points_path)
    quarantine_records = load_quarantine(quarantine_path)
    calibration_reviews = load_reviews(calibration_reviews_path)
    clusters = load_demand_clusters(clusters_path)
    cluster_reviews = load_cluster_reviews(cluster_reviews_path)
    merge_candidates = load_merge_candidates(merge_candidates_path)
    merge_reviews = load_cluster_group_reviews(merge_reviews_path)
    reviewed_groups = load_reviewed_cluster_groups(reviewed_groups_path)

    raw_batch_by_id = {signal.raw_signal_id: _batch_id(signal.batch_id) for signal in raw_signals}
    normalized_batch_by_id = {
        signal.normalized_signal_id: _batch_id(signal.batch_id) for signal in normalized_signals
    }
    normalized_batch_by_raw = {
        signal.raw_signal_id: _batch_id(signal.batch_id) for signal in normalized_signals
    }
    pain_batch_by_id = {
        pain.pain_point_id: _batch_id(pain.batch_id) for pain in pain_points
    }
    pain_batch_by_raw = {
        pain.raw_signal_id: _batch_id(pain.batch_id) for pain in pain_points
    }
    cluster_batches_by_id = {cluster.cluster_id: _batch_ids(cluster.batch_ids) for cluster in clusters}
    candidate_batches_by_id = {
        candidate.merge_candidate_id: _batch_ids(candidate.batch_ids)
        for candidate in merge_candidates
    }
    candidate_pair_by_id = {
        candidate.merge_candidate_id: {candidate.cluster_id_a, candidate.cluster_id_b}
        for candidate in merge_candidates
    }

    counts: dict[str, Counter[str]] = defaultdict(Counter)
    label_counts: dict[str, Counter[str]] = defaultdict(Counter)
    all_batches: set[str] = set()

    def add(batch_ids: Iterable[str], key: str, amount: int = 1) -> None:
        for batch_id in batch_ids:
            all_batches.add(batch_id)
            counts[batch_id][key] += amount

    for signal in raw_signals:
        add([_batch_id(signal.batch_id)], "raw_signals")
    for signal in normalized_signals:
        add([_batch_id(signal.batch_id)], "normalized_signals")
    for pain in pain_points:
        add([_batch_id(pain.batch_id)], "pain_points")
    for record in quarantine_records:
        add(
            [
                _batch_from_quarantine(
                    record,
                    raw_batch_by_id,
                    normalized_batch_by_id,
                    normalized_batch_by_raw,
                )
            ],
            "quarantined_items",
        )
    for cluster in clusters:
        cluster_batch_ids = _batch_ids(cluster.batch_ids)
        add(cluster_batch_ids, "demand_clusters")
        if cluster.evidence_count == 1:
            add(cluster_batch_ids, "singleton_clusters")
    for candidate in merge_candidates:
        add(_batch_ids(candidate.batch_ids), "merge_candidates")
    for group in reviewed_groups:
        add(_batch_ids(group.batch_ids), "reviewed_groups")
    for review in calibration_reviews:
        batch_id = (
            pain_batch_by_id.get(review.pain_point_id or "")
            or pain_batch_by_raw.get(review.raw_signal_id)
            or normalized_batch_by_id.get(review.normalized_signal_id or "")
            or normalized_batch_by_raw.get(review.raw_signal_id)
            or raw_batch_by_id.get(review.raw_signal_id)
            or DEFAULT_BATCH_ID
        )
        add([batch_id], "calibration_reviews")
        label_counts[batch_id][review.label] += 1
    for review in cluster_reviews:
        add(cluster_batches_by_id.get(review.cluster_id, [DEFAULT_BATCH_ID]), "cluster_reviews")
    matching_merge_reviews = [
        review
        for review in merge_reviews
        if candidate_pair_by_id.get(review.merge_candidate_id) == {review.cluster_id_a, review.cluster_id_b}
    ]
    for review in matching_merge_reviews:
        add(candidate_batches_by_id.get(review.merge_candidate_id, [DEFAULT_BATCH_ID]), "merge_reviews")

    if not all_batches:
        all_batches.add(DEFAULT_BATCH_ID)

    created_at = utc_now_iso()
    batch_summaries = [
        _summary_from_counts(batch_id, counts[batch_id], label_counts[batch_id], created_at)
        for batch_id in sorted(all_batches)
    ]
    overall_counts = Counter(
        {
            "raw_signals": len(raw_signals),
            "normalized_signals": len(normalized_signals),
            "pain_points": len(pain_points),
            "quarantined_items": len(quarantine_records),
            "demand_clusters": len(clusters),
            "singleton_clusters": sum(1 for cluster in clusters if cluster.evidence_count == 1),
            "merge_candidates": len(merge_candidates),
            "reviewed_groups": len(reviewed_groups),
            "calibration_reviews": len(calibration_reviews),
            "cluster_reviews": len(cluster_reviews),
            "merge_reviews": len(matching_merge_reviews),
        }
    )
    overall_labels = Counter(review.label for review in calibration_reviews)
    overall = _summary_from_counts("all", overall_counts, overall_labels, created_at)
    return BatchSummaryResult(
        overall=overall,
        batches=batch_summaries,
        readiness=_stage3_readiness(overall),
        generated_at=created_at,
    )


def _summary_from_counts(
    batch_id: str,
    counts: Counter[str],
    labels: Counter[str],
    created_at: str,
) -> BatchSummary:
    raw_signals = counts["raw_signals"]
    normalized_signals = counts["normalized_signals"]
    demand_clusters = counts["demand_clusters"]
    return BatchSummary(
        batch_id=batch_id,
        raw_signals=raw_signals,
        normalized_signals=normalized_signals,
        pain_points=counts["pain_points"],
        quarantined_items=counts["quarantined_items"],
        demand_clusters=demand_clusters,
        singleton_clusters=counts["singleton_clusters"],
        merge_candidates=counts["merge_candidates"],
        reviewed_groups=counts["reviewed_groups"],
        calibration_reviews=counts["calibration_reviews"],
        cluster_reviews=counts["cluster_reviews"],
        merge_reviews=counts["merge_reviews"],
        extraction_yield=_rate(counts["pain_points"], normalized_signals),
        quarantine_rate=_rate(counts["quarantined_items"], raw_signals),
        singleton_rate=_rate(counts["singleton_clusters"], demand_clusters),
        merge_candidate_rate=_rate(counts["merge_candidates"], demand_clusters),
        good_extractions=labels["good_extraction"],
        weak_extractions=labels["weak_extraction"],
        false_positives=labels["false_positive"],
        bad_quotes=labels["bad_quote"],
        should_quarantine=labels["should_quarantine"],
        created_at=created_at,
    )


def _stage3_readiness(overall: BatchSummary) -> Stage3Readiness:
    sample_size_ok = overall.raw_signals >= 50
    pain_volume_ok = overall.pain_points >= 35
    group_volume_ok = overall.reviewed_groups >= 5
    clustering_convergence_ok = (overall.singleton_rate or 0) <= 0.75
    passed = sum([sample_size_ok, pain_volume_ok, group_volume_ok, clustering_convergence_ok])
    if passed == 4:
        ready = "yes"
        recommendation = "样本量、痛点量、聚类收敛和已确认需求组均达标，可以进入真值评分。"
    elif passed >= 2:
        ready = "partial"
        recommendation = "已有部分基础，但建议继续补充人工审核或调校聚类/合并建议后再进入真值评分。"
    else:
        ready = "no"
        recommendation = "证据规模或收敛程度不足，建议继续扩充样本并完成更多人工合并确认。"
    return Stage3Readiness(
        sample_size_ok=sample_size_ok,
        pain_volume_ok=pain_volume_ok,
        group_volume_ok=group_volume_ok,
        clustering_convergence_ok=clustering_convergence_ok,
        ready_for_truth_scoring=ready,
        recommendation=recommendation,
    )


def _batch_from_quarantine(
    record: QuarantineRecord,
    raw_batch_by_id: dict[str, str],
    normalized_batch_by_id: dict[str, str],
    normalized_batch_by_raw: dict[str, str],
) -> str:
    payload = record.raw_payload
    for key in ("raw_signal", "normalized_signal"):
        nested = payload.get(key)
        if isinstance(nested, dict):
            if nested.get("batch_id"):
                return _batch_id(str(nested["batch_id"]))
            if nested.get("raw_signal_id") and str(nested["raw_signal_id"]) in raw_batch_by_id:
                return raw_batch_by_id[str(nested["raw_signal_id"])]
            if nested.get("normalized_signal_id") and str(nested["normalized_signal_id"]) in normalized_batch_by_id:
                return normalized_batch_by_id[str(nested["normalized_signal_id"])]
    candidate = payload.get("candidate")
    if isinstance(candidate, dict):
        if candidate.get("batch_id"):
            return _batch_id(str(candidate["batch_id"]))
        if candidate.get("raw_signal_id") and str(candidate["raw_signal_id"]) in raw_batch_by_id:
            return raw_batch_by_id[str(candidate["raw_signal_id"])]
        if candidate.get("normalized_signal_id") and str(candidate["normalized_signal_id"]) in normalized_batch_by_id:
            return normalized_batch_by_id[str(candidate["normalized_signal_id"])]
    if record.item_id:
        return (
            raw_batch_by_id.get(record.item_id)
            or normalized_batch_by_id.get(record.item_id)
            or normalized_batch_by_raw.get(record.item_id)
            or DEFAULT_BATCH_ID
        )
    return DEFAULT_BATCH_ID


def _batch_ids(values: Iterable[str | None]) -> list[str]:
    result: list[str] = []
    for value in values:
        batch_id = _batch_id(value)
        if batch_id not in result:
            result.append(batch_id)
    return result or [DEFAULT_BATCH_ID]


def _batch_id(value: str | None) -> str:
    text = str(value or "").strip()
    return text or DEFAULT_BATCH_ID


def _rate(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 4)
