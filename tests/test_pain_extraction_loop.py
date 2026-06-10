from pathlib import Path

from demand_radar.loops.pain_extraction_loop import run_pain_extraction
from demand_radar.state.raw_store import read_jsonl, write_jsonl


def test_pain_extraction_loop_writes_valid_points_and_quarantine(tmp_path: Path) -> None:
    normalized_path = tmp_path / "normalized.jsonl"
    output_path = tmp_path / "pain_points.jsonl"
    quarantine_path = tmp_path / "quarantine.jsonl"
    domain_config_path = tmp_path / "domain_config.yaml"
    extraction_config_path = tmp_path / "extraction_config.yaml"
    domain_config_path.write_text(
        "domains:\n  - ai_agent_workflow\npersonas:\n  - developer\nexclude: []\nsignal_types:\n  - complaint\n",
        encoding="utf-8",
    )
    extraction_config_path.write_text(
        "pain_extraction:\n  default_mode: rule_based\n  min_confidence: 0.65\n  max_text_chars: 8000\n",
        encoding="utf-8",
    )
    write_jsonl(
        normalized_path,
        [
            {
                "raw_signal_id": "sig_000001",
                "normalized_signal_id": "norm_000001",
                "source_name": "manual_import",
                "title": "Developer API pain",
                "normalized_text": "Developer API workflow is frustrating and slow every week.",
                "url": None,
                "language": "en",
                "domain_tags": ["ai_agent_workflow"],
                "content_hash": "abc",
            },
            {
                "raw_signal_id": "sig_000002",
                "normalized_signal_id": "norm_000002",
                "source_name": "manual_import",
                "title": "Normal update",
                "normalized_text": "The product launched a new page today.",
                "url": None,
                "language": "en",
                "domain_tags": [],
                "content_hash": "def",
            },
        ],
    )

    pain_points = run_pain_extraction(
        normalized_path,
        output_path,
        quarantine_path,
        domain_config_path,
        extraction_config_path,
    )

    assert len(pain_points) == 1
    assert pain_points[0].evidence_quote == "Developer API workflow is frustrating and slow every week."
    assert len(read_jsonl(output_path)) == 1
    quarantine = read_jsonl(quarantine_path)
    assert len(quarantine) == 1
    assert quarantine[0]["reason"] == "missing_evidence_quote"

