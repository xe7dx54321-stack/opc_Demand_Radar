from pathlib import Path

from demand_radar.clustering.cluster_schema import DemandCluster
from demand_radar.clustering.cluster_store import write_demand_clusters
from demand_radar.clustering.merge_schema import ClusterMergeCandidate
from demand_radar.clustering.merge_store import write_merge_candidates
from demand_radar.config.schemas import NormalizedSignal, PainPoint, RawSignal
from demand_radar.state.processed_store import write_normalized_signals, write_pain_points
from demand_radar.state.raw_store import make_content_hash, utc_now_iso, write_raw_signals
from demand_radar.ui.cluster_review_service import (
    filter_cluster_items_by_batch,
    get_available_cluster_batches,
    load_cluster_review_items,
)
from demand_radar.ui.merge_review_service import (
    filter_merge_items_by_batch,
    get_available_merge_batches,
    load_merge_review_items,
)
from demand_radar.ui.review_service import (
    filter_items_by_batch,
    get_available_batches,
    load_review_items,
)


def test_review_app_imports_with_batch_helpers() -> None:
    from demand_radar.ui import review_app

    assert callable(review_app.main)


def test_pain_review_items_can_filter_by_batch(tmp_path: Path) -> None:
    paths = _write_review_item_fixture(tmp_path)

    items = load_review_items(
        paths["raw"],
        paths["normalized"],
        paths["pain"],
        tmp_path / "quarantine.jsonl",
        tmp_path / "reviews.jsonl",
    )

    assert get_available_batches(items) == ["batch_a", "batch_b"]
    assert len(filter_items_by_batch(items, "All")) == 2
    assert [item.raw_signal_id for item in filter_items_by_batch(items, "batch_a")] == ["sig_000001"]
    assert filter_items_by_batch(items, "missing") == []


def test_cluster_review_items_can_filter_by_batch(tmp_path: Path) -> None:
    clusters_path = tmp_path / "clusters.jsonl"
    write_demand_clusters(
        [
            _cluster("cluster_000001", ["batch_a"]),
            _cluster("cluster_000002", ["batch_b", "batch_c"]),
        ],
        clusters_path,
    )

    items = load_cluster_review_items(clusters_path, tmp_path / "cluster_reviews.jsonl")

    assert get_available_cluster_batches(items) == ["batch_a", "batch_b", "batch_c"]
    assert [item.cluster_id for item in filter_cluster_items_by_batch(items, "batch_b")] == [
        "cluster_000002"
    ]
    assert len(filter_cluster_items_by_batch(items, "All")) == 2


def test_merge_review_items_can_filter_by_batch(tmp_path: Path) -> None:
    candidates_path = tmp_path / "candidates.jsonl"
    write_merge_candidates(
        [
            _candidate("merge_candidate_000001", ["batch_a"]),
            _candidate("merge_candidate_000002", ["batch_b", "batch_c"]),
        ],
        candidates_path,
    )

    items = load_merge_review_items(candidates_path, tmp_path / "merge_reviews.jsonl")

    assert get_available_merge_batches(items) == ["batch_a", "batch_b", "batch_c"]
    assert [
        item.merge_candidate_id for item in filter_merge_items_by_batch(items, "batch_c")
    ] == ["merge_candidate_000002"]
    assert len(filter_merge_items_by_batch(items, "All")) == 2


def _write_review_item_fixture(tmp_path: Path) -> dict[str, Path]:
    raw_path = tmp_path / "raw.jsonl"
    normalized_path = tmp_path / "normalized.jsonl"
    pain_path = tmp_path / "pain.jsonl"
    raw_signals = [
        _raw("sig_000001", "batch_a", "A", "Investor manual tracking is hard."),
        _raw("sig_000002", "batch_b", "B", "Content planning is slow."),
    ]
    write_raw_signals(raw_signals, raw_path)
    write_normalized_signals(
        [
            _normalized(raw_signals[0], "norm_000001"),
            _normalized(raw_signals[1], "norm_000002"),
        ],
        normalized_path,
    )
    write_pain_points(
        [
            _pain("pain_000001", "sig_000001", "norm_000001", "batch_a"),
            _pain("pain_000002", "sig_000002", "norm_000002", "batch_b"),
        ],
        pain_path,
    )
    return {"raw": raw_path, "normalized": normalized_path, "pain": pain_path}


def _raw(signal_id: str, batch_id: str, title: str, text: str) -> RawSignal:
    return RawSignal(
        raw_signal_id=signal_id,
        source_name="manual_import",
        source_type="manual",
        title=title,
        raw_text=text,
        collected_at=utc_now_iso(),
        language="en",
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
        language=raw.language,
        batch_id=raw.batch_id,
        source_note=raw.source_note,
        signal_focus=raw.signal_focus,
        expected_quality=raw.expected_quality,
        content_hash=raw.content_hash,
    )


def _pain(pain_id: str, raw_id: str, normalized_id: str, batch_id: str) -> PainPoint:
    description = "Manual work is hard."
    return PainPoint(
        pain_point_id=pain_id,
        raw_signal_id=raw_id,
        normalized_signal_id=normalized_id,
        persona="investor",
        scenario="test",
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


def _cluster(cluster_id: str, batch_ids: list[str]) -> DemandCluster:
    return DemandCluster(
        cluster_id=cluster_id,
        cluster_title_zh="投资人在产业跟踪中遇到的信息分散问题",
        cluster_summary_zh="投资人在产业跟踪中遇到信息分散和人工整理低效的问题。",
        personas=["investor"],
        domain_tags=["ai_investment_research"],
        workflow_family="ai_investment_research",
        batch_ids=batch_ids,
        signal_focuses=["pain"],
        expected_quality_mix={"strong": 1},
        related_pain_point_ids=[cluster_id.replace("cluster", "pain")],
        evidence_count=1,
        source_count=1,
        representative_pain_descriptions=["信息分散"],
        representative_quotes=["证据说明"],
        current_workarounds=["人工表格"],
        cluster_confidence=0.55,
        cluster_method="rule_similarity_v1",
    )


def _candidate(candidate_id: str, batch_ids: list[str]) -> ClusterMergeCandidate:
    return ClusterMergeCandidate(
        merge_candidate_id=candidate_id,
        cluster_id_a=f"cluster_a_{candidate_id[-6:]}",
        cluster_id_b=f"cluster_b_{candidate_id[-6:]}",
        title_a="投资人在产业跟踪中遇到的信息分散问题",
        title_b="研究员在产业跟踪中遇到的人工整理问题",
        similarity_score=76,
        strength="strong",
        field_scores={"title_similarity": 76},
        shared_keywords=["人工整理"],
        batch_ids=batch_ids,
        merge_reason_zh="这两个需求主题都涉及人工整理耗时，建议人工检查是否可合并。",
    )
