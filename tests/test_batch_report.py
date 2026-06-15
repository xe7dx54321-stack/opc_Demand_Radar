import csv
import json
from pathlib import Path

from demand_radar.batch.batch_report import build_batch_summary_report
from demand_radar.config.schemas import RawSignal
from demand_radar.state.raw_store import make_content_hash, utc_now_iso, write_raw_signals


def test_batch_summary_report_and_quality_matrix_are_generated(tmp_path: Path) -> None:
    raw_path = tmp_path / "raw.jsonl"
    report_path = tmp_path / "batch_summary_report.md"
    matrix_path = tmp_path / "batch_quality_matrix.csv"
    summary_path = tmp_path / "run_summary.json"
    write_raw_signals(
        [
            RawSignal(
                raw_signal_id="sig_000001",
                source_name="manual_import",
                source_type="manual",
                title="Batch sample",
                raw_text="Manual research is hard and scattered.",
                collected_at=utc_now_iso(),
                batch_id="batch_stage26_ai_research",
                content_hash=make_content_hash("Batch sample", "Manual research is hard and scattered."),
            )
        ],
        raw_path,
    )

    result = build_batch_summary_report(
        report_path=report_path,
        matrix_path=matrix_path,
        summary_path=summary_path,
        raw_path=raw_path,
        normalized_path=tmp_path / "normalized.jsonl",
        pain_points_path=tmp_path / "pain.jsonl",
        quarantine_path=tmp_path / "quarantine.jsonl",
        calibration_reviews_path=tmp_path / "reviews.jsonl",
        clusters_path=tmp_path / "clusters.jsonl",
        cluster_reviews_path=tmp_path / "cluster_reviews.jsonl",
        merge_candidates_path=tmp_path / "candidates.jsonl",
        merge_reviews_path=tmp_path / "merge_reviews.jsonl",
        reviewed_groups_path=tmp_path / "groups.jsonl",
        ai_reviewed_groups_path=tmp_path / "ai_groups.jsonl",
        human_exceptions_path=tmp_path / "exceptions.jsonl",
        semantic_judgments_path=tmp_path / "judgments.jsonl",
    )

    report = report_path.read_text(encoding="utf-8")
    matrix_rows = list(csv.DictReader(matrix_path.open("r", encoding="utf-8-sig", newline="")))
    summary_json = json.loads(summary_path.read_text(encoding="utf-8"))
    assert result.overall.raw_signals == 1
    assert "# Batch Summary Report" in report
    assert "batch_stage26_ai_research" in report
    assert "ready_for_truth_scoring: no" in report
    assert matrix_rows[0]["batch_id"] == "batch_stage26_ai_research"
    assert summary_json["batch_count"] == 1
    assert summary_json["ready_for_truth_scoring"] == "no"


def test_batch_summary_report_handles_empty_state(tmp_path: Path) -> None:
    result = build_batch_summary_report(
        report_path=tmp_path / "batch_summary_report.md",
        matrix_path=tmp_path / "batch_quality_matrix.csv",
        summary_path=tmp_path / "run_summary.json",
        raw_path=tmp_path / "raw.jsonl",
        normalized_path=tmp_path / "normalized.jsonl",
        pain_points_path=tmp_path / "pain.jsonl",
        quarantine_path=tmp_path / "quarantine.jsonl",
        calibration_reviews_path=tmp_path / "reviews.jsonl",
        clusters_path=tmp_path / "clusters.jsonl",
        cluster_reviews_path=tmp_path / "cluster_reviews.jsonl",
        merge_candidates_path=tmp_path / "candidates.jsonl",
        merge_reviews_path=tmp_path / "merge_reviews.jsonl",
        reviewed_groups_path=tmp_path / "groups.jsonl",
        ai_reviewed_groups_path=tmp_path / "ai_groups.jsonl",
        human_exceptions_path=tmp_path / "exceptions.jsonl",
        semantic_judgments_path=tmp_path / "judgments.jsonl",
    )

    assert result.overall.raw_signals == 0
    assert [batch.batch_id for batch in result.batches] == ["default"]

