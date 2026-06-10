import json
from pathlib import Path

from demand_radar.config.schemas import PainPoint
from demand_radar.reporting.pain_points_report import build_pain_points_report
from demand_radar.state.raw_store import write_jsonl


def test_pain_points_report_and_summary_are_generated(tmp_path: Path) -> None:
    raw_path = tmp_path / "raw.jsonl"
    normalized_path = tmp_path / "normalized.jsonl"
    pain_path = tmp_path / "pain.jsonl"
    quarantine_path = tmp_path / "quarantine.jsonl"
    report_path = tmp_path / "pain_points_report.md"
    summary_path = tmp_path / "run_summary.json"
    pain_point = PainPoint(
        pain_point_id="pain_000001",
        raw_signal_id="sig_000001",
        normalized_signal_id="norm_000001",
        persona="investor",
        scenario="Tracking AI infra",
        job_to_be_done="track and monitor high-value information across sources",
        current_workaround="manual work",
        pain_description="Tracking AI infra is painful and scattered.",
        pain_intensity=4,
        frequency_signal="weekly",
        payment_signal="labor/time cost signal mentioned",
        evidence_quote="Tracking AI infra is painful and scattered.",
        evidence_span="Tracking AI infra is painful and scattered.",
        confidence=0.82,
        extraction_mode="rule_based",
        extraction_notes="test",
    )
    write_jsonl(
        raw_path,
        [
            {
                "raw_signal_id": "sig_000001",
                "source_name": "manual_import",
                "source_type": "manual",
                "title": "Tracking AI infra",
                "raw_text": "Tracking AI infra is painful and scattered.",
                "url": None,
                "published_at": None,
                "collected_at": "2026-06-10T00:00:00Z",
                "language": "en",
                "domain_tags": ["ai_investment_research"],
                "metadata": {},
                "content_hash": "abc",
            }
        ],
    )
    write_jsonl(
        normalized_path,
        [
            {
                "raw_signal_id": "sig_000001",
                "normalized_signal_id": "norm_000001",
                "source_name": "manual_import",
                "title": "Tracking AI infra",
                "normalized_text": "Tracking AI infra is painful and scattered.",
                "url": None,
                "language": "en",
                "domain_tags": ["ai_investment_research"],
                "content_hash": "abc",
            }
        ],
    )
    write_jsonl(pain_path, [pain_point])
    write_jsonl(quarantine_path, [])

    summary = build_pain_points_report(raw_path, normalized_path, pain_path, quarantine_path, report_path, summary_path)

    report = report_path.read_text(encoding="utf-8")
    summary_json = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary.pain_points == 1
    assert "# Pain Points Report" in report
    assert "Evidence quote: Tracking AI infra is painful and scattered." in report
    assert summary_json["pain_points"] == 1

