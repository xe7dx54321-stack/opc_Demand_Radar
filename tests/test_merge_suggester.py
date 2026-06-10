from pathlib import Path

from demand_radar.clustering.cluster_schema import DemandCluster
from demand_radar.clustering.cluster_store import write_demand_clusters
from demand_radar.clustering.merge_suggester import merge_candidate_gate, suggest_cluster_merges
from demand_radar.state.raw_store import read_jsonl


def make_cluster(
    cluster_id: str,
    title: str,
    summary: str,
    persona: str = "investor",
    domain: str = "ai_investment_research",
    pain: str = "信息分散，人工整理低效",
    workaround: str = "人工表格",
) -> DemandCluster:
    return DemandCluster(
        cluster_id=cluster_id,
        cluster_title_zh=title,
        cluster_summary_zh=summary,
        personas=[persona],
        domain_tags=[domain],
        workflow_family=domain,
        related_pain_point_ids=[f"pain_{cluster_id[-6:]}"],
        evidence_count=1,
        source_count=1,
        representative_pain_descriptions=[pain],
        representative_quotes=["证据说明已经转为中文摘要"],
        current_workarounds=[workaround],
        cluster_confidence=0.55,
        cluster_method="rule_similarity_v1",
    )


def write_merge_config(tmp_path: Path, threshold: int = 62) -> Path:
    config_path = tmp_path / "merge_suggestion_config.yaml"
    config_path.write_text(
        "\n".join(
            [
                "merge_suggestion:",
                "  enabled: true",
                f"  candidate_threshold: {threshold}",
                "  strong_candidate_threshold: 75",
                "  max_candidates_per_cluster: 5",
                "  fields:",
                "    title_weight: 0.20",
                "    summary_weight: 0.25",
                "    pain_description_weight: 0.25",
                "    workaround_weight: 0.10",
                "    persona_weight: 0.10",
                "    domain_weight: 0.10",
            ]
        ),
        encoding="utf-8",
    )
    return config_path


def test_similar_clusters_generate_merge_candidate(tmp_path: Path) -> None:
    clusters_path = tmp_path / "clusters.jsonl"
    candidates_path = tmp_path / "candidates.jsonl"
    invalid_path = tmp_path / "invalid.jsonl"
    config_path = write_merge_config(tmp_path, threshold=62)
    write_demand_clusters(
        [
            make_cluster(
                "cluster_000001",
                "投资人在产业跟踪中遇到的「信息分散、人工整理」问题",
                "投资人在人工智能产业跟踪中遇到信息分散和人工整理低效的问题。",
            ),
            make_cluster(
                "cluster_000002",
                "投资人在产业跟踪中遇到的「信息分散、人工整理低效」问题",
                "投资人跟踪人工智能公司时也遇到信息分散和人工整理低效的问题。",
            ),
        ],
        clusters_path,
    )

    candidates = suggest_cluster_merges(clusters_path, candidates_path, invalid_path, config_path)

    assert len(candidates) == 1
    assert candidates[0].merge_candidate_id == "merge_candidate_000001"
    assert candidates[0].similarity_score >= 62
    assert candidates[0].field_scores["title_similarity"] > 0
    assert "信息分散" in candidates[0].shared_keywords
    assert "建议人工检查是否可合并" in candidates[0].merge_reason_zh
    assert read_jsonl(invalid_path) == []


def test_unrelated_clusters_do_not_generate_candidate(tmp_path: Path) -> None:
    clusters_path = tmp_path / "clusters.jsonl"
    candidates_path = tmp_path / "candidates.jsonl"
    invalid_path = tmp_path / "invalid.jsonl"
    config_path = write_merge_config(tmp_path, threshold=62)
    write_demand_clusters(
        [
            make_cluster(
                "cluster_000001",
                "投资人在产业跟踪中遇到的「信息分散」问题",
                "投资人跟踪人工智能产业时遇到信息分散。",
            ),
            make_cluster(
                "cluster_000002",
                "开发者在工具链中遇到的「文档不完整」问题",
                "开发者查找 SDK 示例时遇到文档不完整和检索困难。",
                persona="developer",
                domain="developer_workflow",
                pain="文档不完整，检索困难",
                workaround="搜索旧 issue",
            ),
        ],
        clusters_path,
    )

    candidates = suggest_cluster_merges(clusters_path, candidates_path, invalid_path, config_path)

    assert candidates == []
    assert read_jsonl(candidates_path) == []


def test_candidate_threshold_and_gate_are_enforced(tmp_path: Path) -> None:
    clusters_path = tmp_path / "clusters.jsonl"
    candidates_path = tmp_path / "candidates.jsonl"
    invalid_path = tmp_path / "invalid.jsonl"
    config_path = write_merge_config(tmp_path, threshold=95)
    write_demand_clusters(
        [
            make_cluster(
                "cluster_000001",
                "投资人在产业跟踪中遇到的「信息分散」问题",
                "投资人跟踪人工智能产业时遇到信息分散。",
            ),
            make_cluster(
                "cluster_000002",
                "投资人在产业跟踪中遇到的「信息分散、人工整理」问题",
                "投资人跟踪人工智能产业时遇到信息分散和人工整理低效。",
            ),
        ],
        clusters_path,
    )

    candidates = suggest_cluster_merges(clusters_path, candidates_path, invalid_path, config_path)

    assert candidates == []
    weaker_config = write_merge_config(tmp_path, threshold=50)
    weaker_candidates = suggest_cluster_merges(
        clusters_path,
        candidates_path,
        invalid_path,
        weaker_config,
    )
    assert weaker_candidates
    assert merge_candidate_gate(weaker_candidates[0], 50)
    assert not merge_candidate_gate(weaker_candidates[0], 101)
