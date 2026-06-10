from pathlib import Path

from demand_radar.clustering.cluster_schema import DemandCluster
from demand_radar.clustering.demand_clusterer import cluster_gate, run_demand_clustering
from demand_radar.state.raw_store import read_jsonl, write_jsonl


def pain_row(
    pain_point_id: str,
    raw_signal_id: str,
    persona: str,
    pain_description: str,
    job_to_be_done: str,
    current_workaround: str,
) -> dict[str, object]:
    return {
        "pain_point_id": pain_point_id,
        "raw_signal_id": raw_signal_id,
        "normalized_signal_id": pain_point_id.replace("pain", "norm"),
        "persona": persona,
        "scenario": job_to_be_done,
        "job_to_be_done": job_to_be_done,
        "current_workaround": current_workaround,
        "pain_description": pain_description,
        "pain_intensity": 4,
        "frequency_signal": "weekly",
        "payment_signal": None,
        "evidence_quote": pain_description,
        "evidence_span": pain_description,
        "confidence": 0.8,
        "extraction_mode": "rule_based",
        "extraction_notes": None,
    }


def write_cluster_config(tmp_path: Path, threshold: int = 70) -> Path:
    config = tmp_path / "clustering_config.yaml"
    config.write_text(
        "\n".join(
            [
                "clustering:",
                "  enabled: true",
                f"  similarity_threshold: {threshold}",
                "  singleton_clusters: true",
                "  max_representative_quotes: 3",
            ]
        ),
        encoding="utf-8",
    )
    return config


def test_similar_pain_points_cluster_together(tmp_path: Path) -> None:
    pain_path = tmp_path / "pain.jsonl"
    clusters_path = tmp_path / "clusters.jsonl"
    invalid_path = tmp_path / "invalid.jsonl"
    config_path = write_cluster_config(tmp_path, threshold=70)
    write_jsonl(
        pain_path,
        [
            pain_row(
                "pain_000001",
                "sig_000001",
                "investor",
                "manual AI company tracking is slow and scattered",
                "track AI company updates",
                "manual spreadsheet",
            ),
            pain_row(
                "pain_000002",
                "sig_000002",
                "investor",
                "manual AI company tracking is too slow and scattered",
                "track AI company updates",
                "manual spreadsheet",
            ),
        ],
    )

    clusters = run_demand_clustering(pain_path, clusters_path, invalid_path, config_path)

    assert len(clusters) == 1
    assert clusters[0].evidence_count == 2
    assert "问题" in clusters[0].cluster_title_zh
    assert read_jsonl(invalid_path) == []


def test_unrelated_pain_points_remain_singleton_clusters(tmp_path: Path) -> None:
    pain_path = tmp_path / "pain.jsonl"
    clusters_path = tmp_path / "clusters.jsonl"
    invalid_path = tmp_path / "invalid.jsonl"
    config_path = write_cluster_config(tmp_path, threshold=70)
    write_jsonl(
        pain_path,
        [
            pain_row(
                "pain_000001",
                "sig_000001",
                "investor",
                "manual AI company tracking is slow and scattered",
                "track AI company updates",
                "manual spreadsheet",
            ),
            pain_row(
                "pain_000002",
                "sig_000002",
                "developer",
                "SDK docs are incomplete and hard to search",
                "find SDK examples",
                "search GitHub issues",
            ),
        ],
    )

    clusters = run_demand_clustering(pain_path, clusters_path, invalid_path, config_path)

    assert len(clusters) == 2
    assert all(cluster.evidence_count == 1 for cluster in clusters)
    assert all(cluster.cluster_summary_zh for cluster in clusters)


def test_cluster_gate_rejects_low_confidence_cluster() -> None:
    cluster = DemandCluster(
        cluster_id="cluster_000001",
        cluster_title_zh="相关用户在工作流中遇到的问题",
        cluster_summary_zh="这是一个候选需求主题。",
        related_pain_point_ids=["pain_000001"],
        evidence_count=1,
        source_count=1,
        cluster_confidence=0.49,
        cluster_method="rule_similarity_v1",
    )

    assert not cluster_gate(cluster)
