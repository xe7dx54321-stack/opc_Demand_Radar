from pathlib import Path

from demand_radar.batch.batch_summary import build_batch_summary
from demand_radar.calibration.review_store import append_review
from demand_radar.clustering.cluster_review_schema import ClusterReview
from demand_radar.clustering.cluster_schema import DemandCluster
from demand_radar.clustering.cluster_store import write_demand_clusters
from demand_radar.clustering.merge_schema import ClusterGroupReview, ClusterMergeCandidate, ReviewedClusterGroup
from demand_radar.clustering.merge_store import (
    write_merge_candidates,
    write_reviewed_cluster_groups,
)
from demand_radar.config.schemas import NormalizedSignal, PainPoint, RawSignal
from demand_radar.state.processed_store import write_normalized_signals, write_pain_points
from demand_radar.state.quarantine_store import append_quarantine
from demand_radar.state.raw_store import make_content_hash, utc_now_iso, write_jsonl, write_raw_signals


def test_build_batch_summary_counts_pipeline_state_by_batch(tmp_path: Path) -> None:
    paths = _write_batch_fixture(tmp_path)

    result = build_batch_summary(
        raw_path=paths["raw"],
        normalized_path=paths["normalized"],
        pain_points_path=paths["pain"],
        quarantine_path=paths["quarantine"],
        calibration_reviews_path=paths["calibration_reviews"],
        clusters_path=paths["clusters"],
        cluster_reviews_path=paths["cluster_reviews"],
        merge_candidates_path=paths["merge_candidates"],
        merge_reviews_path=paths["merge_reviews"],
        reviewed_groups_path=paths["reviewed_groups"],
    )

    batches = {batch.batch_id: batch for batch in result.batches}
    assert result.overall.raw_signals == 3
    assert result.overall.pain_points == 2
    assert result.overall.quarantined_items == 1
    assert result.overall.demand_clusters == 2
    assert result.overall.merge_candidates == 1
    assert result.overall.reviewed_groups == 1
    assert result.readiness.ready_for_truth_scoring == "no"
    assert batches["batch_a"].raw_signals == 2
    assert batches["batch_a"].pain_points == 1
    assert batches["batch_a"].quarantined_items == 1
    assert batches["batch_a"].good_extractions == 1
    assert batches["batch_b"].raw_signals == 1
    assert batches["batch_b"].pain_points == 1
    assert batches["batch_b"].bad_quotes == 1


def test_build_batch_summary_defaults_missing_batch_to_default(tmp_path: Path) -> None:
    raw_path = tmp_path / "raw.jsonl"
    normalized_path = tmp_path / "normalized.jsonl"
    pain_path = tmp_path / "pain.jsonl"
    write_raw_signals(
        [
            RawSignal(
                raw_signal_id="sig_000001",
                source_name="manual_import",
                source_type="manual",
                title="No batch",
                raw_text="Manual tracking is hard.",
                collected_at=utc_now_iso(),
                content_hash=make_content_hash("No batch", "Manual tracking is hard."),
            )
        ],
        raw_path,
    )
    write_normalized_signals([], normalized_path)
    write_pain_points([], pain_path)

    result = build_batch_summary(
        raw_path=raw_path,
        normalized_path=normalized_path,
        pain_points_path=pain_path,
        quarantine_path=tmp_path / "quarantine.jsonl",
        calibration_reviews_path=tmp_path / "reviews.jsonl",
        clusters_path=tmp_path / "clusters.jsonl",
        cluster_reviews_path=tmp_path / "cluster_reviews.jsonl",
        merge_candidates_path=tmp_path / "candidates.jsonl",
        merge_reviews_path=tmp_path / "merge_reviews.jsonl",
        reviewed_groups_path=tmp_path / "groups.jsonl",
    )

    assert [batch.batch_id for batch in result.batches] == ["default"]
    assert result.batches[0].raw_signals == 1


def test_build_batch_summary_ignores_stale_merge_reviews_with_changed_pair(tmp_path: Path) -> None:
    paths = _write_batch_fixture(tmp_path)
    write_jsonl(
        paths["merge_reviews"],
        [
            ClusterGroupReview(
                review_id="cluster_group_review_000001",
                merge_candidate_id="merge_candidate_000001",
                cluster_id_a="cluster_000009",
                cluster_id_b="cluster_000010",
                label="confirm_merge",
            )
        ],
    )

    result = build_batch_summary(
        raw_path=paths["raw"],
        normalized_path=paths["normalized"],
        pain_points_path=paths["pain"],
        quarantine_path=paths["quarantine"],
        calibration_reviews_path=paths["calibration_reviews"],
        clusters_path=paths["clusters"],
        cluster_reviews_path=paths["cluster_reviews"],
        merge_candidates_path=paths["merge_candidates"],
        merge_reviews_path=paths["merge_reviews"],
        reviewed_groups_path=paths["reviewed_groups"],
    )

    assert result.overall.merge_reviews == 0
    assert all(batch.merge_reviews == 0 for batch in result.batches)


def _write_batch_fixture(tmp_path: Path) -> dict[str, Path]:
    paths = {
        "raw": tmp_path / "raw.jsonl",
        "normalized": tmp_path / "normalized.jsonl",
        "pain": tmp_path / "pain.jsonl",
        "quarantine": tmp_path / "quarantine.jsonl",
        "calibration_reviews": tmp_path / "calibration_reviews.jsonl",
        "clusters": tmp_path / "clusters.jsonl",
        "cluster_reviews": tmp_path / "cluster_reviews.jsonl",
        "merge_candidates": tmp_path / "merge_candidates.jsonl",
        "merge_reviews": tmp_path / "merge_reviews.jsonl",
        "reviewed_groups": tmp_path / "reviewed_groups.jsonl",
    }
    raw_signals = [
        _raw("sig_000001", "batch_a", "Investor pain", "Manual research is hard and scattered."),
        _raw("sig_000002", "batch_a", "Noise", "Product launch note only."),
        _raw("sig_000003", "batch_b", "Content pain", "Content planning is manual and slow."),
    ]
    write_raw_signals(raw_signals, paths["raw"])
    write_normalized_signals(
        [
            _normalized(raw_signals[0], "norm_000001"),
            _normalized(raw_signals[1], "norm_000002"),
            _normalized(raw_signals[2], "norm_000003"),
        ],
        paths["normalized"],
    )
    write_pain_points(
        [
            _pain("pain_000001", "sig_000001", "norm_000001", "batch_a", "investor"),
            _pain("pain_000002", "sig_000003", "norm_000003", "batch_b", "content_team"),
        ],
        paths["pain"],
    )
    append_quarantine(
        "pain_point",
        "missing_evidence_quote",
        {
            "normalized_signal": {
                "raw_signal_id": "sig_000002",
                "normalized_signal_id": "norm_000002",
                "batch_id": "batch_a",
                "normalized_text": "Product launch note only.",
            }
        },
        item_id="norm_000002",
        path=paths["quarantine"],
    )
    append_review(
        "sig_000001",
        "good_extraction",
        "looks right",
        normalized_signal_id="norm_000001",
        pain_point_id="pain_000001",
        path=paths["calibration_reviews"],
    )
    append_review(
        "sig_000003",
        "bad_quote",
        "quote thin",
        normalized_signal_id="norm_000003",
        pain_point_id="pain_000002",
        path=paths["calibration_reviews"],
    )
    write_demand_clusters(
        [
            _cluster("cluster_000001", ["pain_000001"], ["batch_a"]),
            _cluster("cluster_000002", ["pain_000002"], ["batch_b"]),
        ],
        paths["clusters"],
    )
    write_jsonl(
        paths["cluster_reviews"],
        [ClusterReview(review_id="cluster_review_000001", cluster_id="cluster_000001", label="good_cluster")],
    )
    write_merge_candidates(
        [_candidate("merge_candidate_000001", ["batch_a", "batch_b"])],
        paths["merge_candidates"],
    )
    write_jsonl(
        paths["merge_reviews"],
        [
            ClusterGroupReview(
                review_id="cluster_group_review_000001",
                merge_candidate_id="merge_candidate_000001",
                cluster_id_a="cluster_000001",
                cluster_id_b="cluster_000002",
                label="confirm_merge",
            )
        ],
    )
    write_reviewed_cluster_groups(
        [_group(["cluster_000001", "cluster_000002"], ["batch_a", "batch_b"])],
        paths["reviewed_groups"],
    )
    return paths


def _raw(signal_id: str, batch_id: str, title: str, text: str) -> RawSignal:
    return RawSignal(
        raw_signal_id=signal_id,
        source_name="manual_import",
        source_type="manual",
        title=title,
        raw_text=text,
        collected_at=utc_now_iso(),
        language="en",
        domain_tags=["ai_investment_research"],
        batch_id=batch_id,
        source_note="test excerpt",
        signal_focus="pain",
        expected_quality="strong",
        content_hash=make_content_hash(title, text),
    )


def _normalized(raw: RawSignal, normalized_id: str) -> NormalizedSignal:
    return NormalizedSignal(
        raw_signal_id=raw.raw_signal_id,
        normalized_signal_id=normalized_id,
        source_name=raw.source_name,
        title=raw.title,
        normalized_text=raw.raw_text,
        url=raw.url,
        language=raw.language,
        domain_tags=raw.domain_tags,
        batch_id=raw.batch_id,
        source_note=raw.source_note,
        signal_focus=raw.signal_focus,
        expected_quality=raw.expected_quality,
        content_hash=raw.content_hash,
    )


def _pain(pain_id: str, raw_id: str, norm_id: str, batch_id: str, persona: str) -> PainPoint:
    description = "Manual work is hard and scattered."
    return PainPoint(
        pain_point_id=pain_id,
        raw_signal_id=raw_id,
        normalized_signal_id=norm_id,
        persona=persona,
        scenario="Research workflow",
        job_to_be_done="track work",
        current_workaround="manual spreadsheet",
        pain_description=description,
        evidence_quote=description,
        confidence=0.82,
        extraction_mode="rule_based",
        batch_id=batch_id,
        signal_focus="pain",
        expected_quality="strong",
    )


def _cluster(cluster_id: str, pain_ids: list[str], batch_ids: list[str]) -> DemandCluster:
    return DemandCluster(
        cluster_id=cluster_id,
        cluster_title_zh="投资人在产业跟踪中遇到的信息分散问题",
        cluster_summary_zh="投资人在产业跟踪中反复遇到信息分散和人工整理低效的问题。",
        personas=["investor"],
        domain_tags=["ai_investment_research"],
        workflow_family="ai_investment_research",
        batch_ids=batch_ids,
        signal_focuses=["pain"],
        expected_quality_mix={"strong": len(pain_ids)},
        related_pain_point_ids=pain_ids,
        evidence_count=len(pain_ids),
        source_count=len(pain_ids),
        representative_pain_descriptions=["信息分散"],
        representative_quotes=["证据说明"],
        current_workarounds=["人工表格"],
        cluster_confidence=0.55,
        cluster_method="rule_similarity_v1",
    )


def _candidate(candidate_id: str, batch_ids: list[str]) -> ClusterMergeCandidate:
    return ClusterMergeCandidate(
        merge_candidate_id=candidate_id,
        cluster_id_a="cluster_000001",
        cluster_id_b="cluster_000002",
        title_a="投资人在产业跟踪中遇到的信息分散问题",
        title_b="内容团队在选题中遇到的人工整理问题",
        similarity_score=76,
        strength="strong",
        field_scores={"title_similarity": 76},
        shared_keywords=["人工整理"],
        batch_ids=batch_ids,
        merge_reason_zh="这两个需求主题都涉及人工整理耗时，建议人工检查是否可合并。",
    )


def _group(cluster_ids: list[str], batch_ids: list[str]) -> ReviewedClusterGroup:
    return ReviewedClusterGroup(
        group_id="cluster_group_000001",
        group_title_zh="相关用户在信息整理中遇到的人工整理问题",
        group_summary_zh="相关用户在信息整理中遇到人工整理耗时和信息分散的问题。",
        cluster_ids=cluster_ids,
        related_pain_point_ids=["pain_000001", "pain_000002"],
        batch_ids=batch_ids,
        evidence_count=2,
        source_count=2,
    )
