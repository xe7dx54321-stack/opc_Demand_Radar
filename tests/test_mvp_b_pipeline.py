"""Tests for MVP-B pipeline."""
import pytest
from pathlib import Path
from demand_radar.mvp_b.mvp_b_pipeline import run_mvp_b, MVPBRunSummary


def test_empty_candidates_returns_gracefully(tmp_path):
    """Pipeline gracefully returns when no candidates found."""
    fake_path = tmp_path / "nonexistent.jsonl"
    result = run_mvp_b(
        domain_id="ai_investment_tracking",
        candidates_path=fake_path,
    )
    assert isinstance(result, MVPBRunSummary)
    assert result.candidates_processed == 0
    assert result.errors  # should report error


def test_pipeline_runs_with_candidates(tmp_path):
    """Pipeline runs with a few candidates (no LLM)."""
    import json
    cands_path = tmp_path / "candidates.jsonl"
    candidates = [
        {
            "candidate_id": f"c{i:03d}",
            "title": f"Investment Research Tool {i}",
            "raw_text": "VC analysts spend hours tracking AI startups for deal sourcing and market intelligence. "
                        "Current solution is spreadsheets and manual tracking.",
            "source_type": "community_discussion",
            "source_url": f"https://news.ycombinator.com/item?id={i}",
            "detected_signal_types": ["workflow_signal"],
            "validation_status": "valid",
        }
        for i in range(5)
    ]
    cands_path.write_text(
        "\n".join(json.dumps(c, ensure_ascii=False) for c in candidates),
        encoding="utf-8",
    )

    result = run_mvp_b(
        domain_id="ai_investment_tracking",
        candidates_path=cands_path,
        llm_client=None,
        relevance_output=tmp_path / "rel.jsonl",
        pain_output=tmp_path / "pain.jsonl",
        filled_csv_output=tmp_path / "filled.csv",
    )

    assert isinstance(result, MVPBRunSummary)
    assert result.candidates_processed == 5
    # With no LLM, investments-related candidates could be include by rules
    assert result.include_count + result.uncertain_count + result.exclude_count == 5
    assert result.filled_csv is not None
    assert (tmp_path / "filled.csv").exists()


def test_pipeline_summary_fields():
    result = MVPBRunSummary(
        domain_id="test",
        candidates_processed=10,
        include_count=5,
        uncertain_count=3,
        exclude_count=2,
        pain_processed=8,
        should_extract_count=4,
        strong_count=1,
        medium_count=3,
    )
    assert result.include_count == 5
    assert result.strong_count == 1
    assert result.errors == []
