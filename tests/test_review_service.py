from pathlib import Path

from demand_radar.calibration.review_store import append_review, load_reviews
from demand_radar.state.quarantine_store import append_quarantine
from demand_radar.state.raw_store import write_jsonl
from demand_radar.ui.review_service import add_review, evidence_quote_found, get_review_summary, load_review_items


def write_review_fixture(tmp_path: Path) -> dict[str, Path]:
    paths = {
        "raw": tmp_path / "raw.jsonl",
        "normalized": tmp_path / "normalized.jsonl",
        "pain": tmp_path / "pain.jsonl",
        "quarantine": tmp_path / "quarantine.jsonl",
        "reviews": tmp_path / "reviews.jsonl",
    }
    write_jsonl(
        paths["raw"],
        [
            {
                "raw_signal_id": "sig_000001",
                "source_name": "manual_import",
                "source_type": "manual",
                "title": "Developer API pain",
                "raw_text": "Developer API workflow is frustrating and slow every week.",
                "url": "https://example.com/1",
                "published_at": None,
                "collected_at": "2026-06-10T00:00:00Z",
                "language": "en",
                "domain_tags": ["ai_agent_workflow"],
                "metadata": {},
                "content_hash": "abc",
            },
            {
                "raw_signal_id": "sig_000002",
                "source_name": "manual_import",
                "source_type": "manual",
                "title": "Normal update",
                "raw_text": "The product launched a new page today.",
                "url": "https://example.com/2",
                "published_at": None,
                "collected_at": "2026-06-10T00:00:00Z",
                "language": "en",
                "domain_tags": [],
                "metadata": {},
                "content_hash": "def",
            },
        ],
    )
    write_jsonl(
        paths["normalized"],
        [
            {
                "raw_signal_id": "sig_000001",
                "normalized_signal_id": "norm_000001",
                "source_name": "manual_import",
                "title": "Developer API pain",
                "normalized_text": "Developer API workflow is frustrating and slow every week.",
                "url": "https://example.com/1",
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
                "url": "https://example.com/2",
                "language": "en",
                "domain_tags": [],
                "content_hash": "def",
            },
        ],
    )
    write_jsonl(
        paths["pain"],
        [
            {
                "pain_point_id": "pain_000001",
                "raw_signal_id": "sig_000001",
                "normalized_signal_id": "norm_000001",
                "persona": "developer",
                "scenario": "Developer API pain",
                "job_to_be_done": "complete developer workflow with less friction",
                "current_workaround": None,
                "pain_description": "Developer API workflow is frustrating and slow every week.",
                "pain_intensity": 4,
                "frequency_signal": "weekly",
                "payment_signal": None,
                "evidence_quote": "Developer API workflow is frustrating and slow every week.",
                "evidence_span": "Developer API workflow is frustrating and slow every week.",
                "confidence": 0.82,
                "extraction_mode": "rule_based",
                "extraction_notes": "test",
            }
        ],
    )
    write_jsonl(paths["quarantine"], [])
    write_jsonl(paths["reviews"], [])
    append_quarantine(
        "pain_point",
        "missing_evidence_quote",
        {
            "candidate": {
                "pain_point_id": "pain_000002",
                "raw_signal_id": "sig_000002",
                "normalized_signal_id": "norm_000002",
                "pain_description": "",
                "evidence_quote": "",
                "confidence": 0.2,
            },
            "normalized_signal": {
                "raw_signal_id": "sig_000002",
                "normalized_signal_id": "norm_000002",
                "normalized_text": "The product launched a new page today.",
            },
        },
        item_id="pain_000002",
        path=paths["quarantine"],
    )
    return paths


def test_load_review_items_merges_pipeline_state(tmp_path: Path) -> None:
    paths = write_review_fixture(tmp_path)

    items = load_review_items(
        paths["raw"],
        paths["normalized"],
        paths["pain"],
        paths["quarantine"],
        paths["reviews"],
    )

    assert len(items) == 2
    pain_item = next(item for item in items if item.item_type == "pain_point")
    quarantine_item = next(item for item in items if item.item_type == "quarantine")
    assert pain_item.evidence_quote == "Developer API workflow is frustrating and slow every week."
    assert pain_item.persona == "developer"
    assert evidence_quote_found(pain_item)
    assert quarantine_item.quarantine_reason == "missing_evidence_quote"
    assert quarantine_item.normalized_signal_id == "norm_000002"


def test_review_summary_counts_reviewed_and_labels(tmp_path: Path) -> None:
    paths = write_review_fixture(tmp_path)
    append_review(
        raw_signal_id="sig_000001",
        normalized_signal_id="norm_000001",
        pain_point_id="pain_000001",
        label="good_extraction",
        reviewer_note="Looks right.",
        path=paths["reviews"],
    )

    items = load_review_items(
        paths["raw"],
        paths["normalized"],
        paths["pain"],
        paths["quarantine"],
        paths["reviews"],
    )
    summary = get_review_summary(items, paths["raw"], paths["normalized"], paths["pain"], paths["quarantine"])

    assert summary.raw_signals == 2
    assert summary.normalized_signals == 2
    assert summary.pain_points == 1
    assert summary.quarantine == 1
    assert summary.reviewed == 1
    assert summary.unreviewed == 1
    assert summary.labels["good_extraction"] == 1


def test_add_review_does_not_mutate_pain_points(tmp_path: Path) -> None:
    paths = write_review_fixture(tmp_path)
    items = load_review_items(
        paths["raw"],
        paths["normalized"],
        paths["pain"],
        paths["quarantine"],
        paths["reviews"],
    )
    pain_item = next(item for item in items if item.item_type == "pain_point")
    before = paths["pain"].read_text(encoding="utf-8")

    review = add_review(pain_item, "bad_quote", "Quote is too narrow.", reviews_path=paths["reviews"])
    after = paths["pain"].read_text(encoding="utf-8")

    assert review.review_id == "review_000001"
    assert load_reviews(paths["reviews"])[0].label == "bad_quote"
    assert before == after
