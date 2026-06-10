import json
from pathlib import Path

from demand_radar.calibration.calibration_review import append_calibration_review
from demand_radar.reporting.calibration_report import build_calibration_report
from demand_radar.state.raw_store import write_jsonl


def write_minimal_pipeline_files(tmp_path: Path) -> dict[str, Path]:
    paths = {
        "raw": tmp_path / "raw.jsonl",
        "normalized": tmp_path / "normalized.jsonl",
        "pain": tmp_path / "pain.jsonl",
        "quarantine": tmp_path / "quarantine.jsonl",
        "reviews": tmp_path / "reviews.jsonl",
        "report": tmp_path / "calibration_report.md",
        "summary": tmp_path / "run_summary.json",
        "config": tmp_path / "calibration_config.yaml",
    }
    write_jsonl(
        paths["raw"],
        [
            {
                "raw_signal_id": "sig_000001",
                "source_name": "manual_import",
                "source_type": "manual",
                "title": "API pain",
                "raw_text": "Developer API docs are incomplete and slow to use.",
                "url": None,
                "published_at": None,
                "collected_at": "2026-06-10T00:00:00Z",
                "language": "en",
                "domain_tags": ["ai_agent_workflow"],
                "metadata": {},
                "content_hash": "abc",
            }
        ],
    )
    write_jsonl(
        paths["normalized"],
        [
            {
                "raw_signal_id": "sig_000001",
                "normalized_signal_id": "norm_000001",
                "source_name": "manual_import",
                "title": "API pain",
                "normalized_text": "Developer API docs are incomplete and slow to use.",
                "url": None,
                "language": "en",
                "domain_tags": ["ai_agent_workflow"],
                "content_hash": "abc",
            }
        ],
    )
    write_jsonl(paths["pain"], [])
    write_jsonl(paths["quarantine"], [])
    write_jsonl(paths["reviews"], [])
    paths["config"].write_text(
        "calibration:\n  report:\n    include_examples: true\n    max_examples_per_label: 10\n",
        encoding="utf-8",
    )
    return paths


def test_calibration_report_generates_without_reviews(tmp_path: Path) -> None:
    paths = write_minimal_pipeline_files(tmp_path)

    summary = build_calibration_report(
        paths["raw"],
        paths["normalized"],
        paths["pain"],
        paths["quarantine"],
        paths["reviews"],
        paths["report"],
        paths["summary"],
        paths["config"],
    )

    report = paths["report"].read_text(encoding="utf-8")
    summary_json = json.loads(paths["summary"].read_text(encoding="utf-8"))
    assert summary.calibration_reviews == 0
    assert "# Extraction Calibration Report" in report
    assert "### good_extraction" in report
    assert "### false_positive" in report
    assert "### false_negative" in report
    assert summary_json["calibration_reviews"] == 0


def test_calibration_report_groups_reviews(tmp_path: Path) -> None:
    paths = write_minimal_pipeline_files(tmp_path)
    append_calibration_review(
        raw_signal_id="sig_000001",
        pain_point_id="pain_000001",
        label="good_extraction",
        reviewer_note="Useful evidence quote.",
        path=paths["reviews"],
    )
    append_calibration_review(
        raw_signal_id="sig_000002",
        label="false_negative",
        reviewer_note="Clear pain was missed.",
        path=paths["reviews"],
    )

    build_calibration_report(
        paths["raw"],
        paths["normalized"],
        paths["pain"],
        paths["quarantine"],
        paths["reviews"],
        paths["report"],
        paths["summary"],
        paths["config"],
    )

    report = paths["report"].read_text(encoding="utf-8")
    assert "- Good extraction: 1" in report
    assert "- False negative: 1" in report
    assert "Useful evidence quote." in report
    assert "Clear pain was missed." in report
