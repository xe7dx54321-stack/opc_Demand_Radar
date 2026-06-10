from pathlib import Path

from demand_radar.clustering.merge_schema import ClusterMergeCandidate
from demand_radar.clustering.merge_store import (
    append_cluster_group_review,
    get_latest_review_for_candidate,
    load_cluster_group_reviews,
    load_merge_candidates,
    write_merge_candidates,
)


def make_candidate(candidate_id: str = "merge_candidate_000001") -> ClusterMergeCandidate:
    return ClusterMergeCandidate(
        merge_candidate_id=candidate_id,
        cluster_id_a="cluster_000001",
        cluster_id_b="cluster_000002",
        title_a="投资人在产业跟踪中遇到的「信息分散」问题",
        title_b="投资人在产业跟踪中遇到的「人工整理低效」问题",
        similarity_score=78.5,
        strength="strong",
        field_scores={"title_similarity": 80.0},
        shared_personas=["investor"],
        shared_domain_tags=["ai_investment_research"],
        shared_keywords=["信息分散"],
        merge_reason_zh="这两个需求主题的核心痛点相似，建议人工检查是否可合并为同一类需求。",
        representative_quotes_a=["证据说明 A"],
        representative_quotes_b=["证据说明 B"],
    )


def test_merge_candidates_can_be_written_and_loaded(tmp_path: Path) -> None:
    path = tmp_path / "cluster_merge_candidates.jsonl"
    candidate = make_candidate()

    count = write_merge_candidates([candidate], path)
    loaded = load_merge_candidates(path)

    assert count == 1
    assert loaded[0].merge_candidate_id == "merge_candidate_000001"
    assert loaded[0].shared_keywords == ["信息分散"]


def test_cluster_group_reviews_append_and_latest_review_wins(tmp_path: Path) -> None:
    reviews_path = tmp_path / "cluster_group_reviews.jsonl"

    first = append_cluster_group_review(
        "merge_candidate_000001",
        "cluster_000001",
        "cluster_000002",
        "maybe_merge",
        reviewer_note="还需要进一步确认。",
        path=reviews_path,
    )
    second = append_cluster_group_review(
        "merge_candidate_000001",
        "cluster_000001",
        "cluster_000002",
        "confirm_merge",
        reviewer_note="人工确认属于同一需求。",
        expected_group_title_zh="投资人在产业跟踪中遇到的信息整理问题",
        path=reviews_path,
    )

    reviews = load_cluster_group_reviews(reviews_path)
    latest = get_latest_review_for_candidate("merge_candidate_000001", path=reviews_path)

    assert [review.review_id for review in reviews] == [first.review_id, second.review_id]
    assert latest is not None
    assert latest.label == "confirm_merge"
    assert latest.expected_group_title_zh == "投资人在产业跟踪中遇到的信息整理问题"


def test_empty_review_file_is_safe(tmp_path: Path) -> None:
    reviews_path = tmp_path / "missing_reviews.jsonl"

    assert load_cluster_group_reviews(reviews_path) == []
    assert get_latest_review_for_candidate("merge_candidate_000001", path=reviews_path) is None
