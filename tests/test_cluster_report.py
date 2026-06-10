import json
from pathlib import Path

from demand_radar.clustering.cluster_store import append_cluster_review, write_demand_clusters
from demand_radar.clustering.cluster_report import build_cluster_report
from demand_radar.clustering.cluster_schema import DemandCluster
from demand_radar.state.raw_store import write_jsonl


def make_cluster() -> DemandCluster:
    return DemandCluster(
        cluster_id="cluster_000001",
        cluster_title_zh="投资人在产业跟踪中遇到的信息分散问题",
        cluster_summary_zh="投资人在跟踪人工智能产业时反复遇到信息分散和人工整理低效的问题。",
        personas=["investor"],
        domain_tags=["ai_investment_research"],
        workflow_family="ai_investment_research",
        related_pain_point_ids=["pain_000001"],
        evidence_count=1,
        source_count=1,
        representative_pain_descriptions=["信息分散，人工整理低效"],
        representative_quotes=["证据说明已经转为中文摘要"],
        current_workarounds=["人工表格"],
        cluster_confidence=0.55,
        cluster_method="rule_similarity_v1",
    )


def test_cluster_report_generates_markdown_and_summary(tmp_path: Path) -> None:
    pain_path = tmp_path / "pain.jsonl"
    clusters_path = tmp_path / "clusters.jsonl"
    reviews_path = tmp_path / "reviews.jsonl"
    invalid_path = tmp_path / "invalid.jsonl"
    report_path = tmp_path / "demand_clusters_report.md"
    summary_path = tmp_path / "run_summary.json"
    write_jsonl(
        pain_path,
        [
            {
                "pain_point_id": "pain_000001",
                "raw_signal_id": "sig_000001",
                "normalized_signal_id": "norm_000001",
                "persona": "investor",
                "scenario": "tracking AI companies",
                "job_to_be_done": "track AI company updates",
                "current_workaround": "manual spreadsheet",
                "pain_description": "manual AI company tracking is slow and scattered",
                "pain_intensity": 4,
                "frequency_signal": "weekly",
                "payment_signal": None,
                "evidence_quote": "manual AI company tracking is slow and scattered",
                "evidence_span": "manual AI company tracking is slow and scattered",
                "confidence": 0.8,
                "extraction_mode": "rule_based",
                "extraction_notes": None,
            }
        ],
    )
    write_demand_clusters([make_cluster()], clusters_path)
    append_cluster_review("cluster_000001", "good_cluster", "主题可用。", path=reviews_path)
    write_jsonl(invalid_path, [])

    summary = build_cluster_report(
        pain_path,
        clusters_path,
        reviews_path,
        invalid_path,
        report_path,
        summary_path,
    )

    report = report_path.read_text(encoding="utf-8")
    summary_json = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary.demand_clusters == 1
    assert summary.reviewed_clusters == 1
    assert "投资人在产业跟踪中遇到的信息分散问题" in report
    assert "审核状态：通过" in report
    assert summary_json["demand_clusters"] == 1
    assert summary_json["cluster_reviews"] == 1
