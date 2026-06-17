"""Shared fixtures for D5 tests."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + ("\n" if rows else ""),
        encoding="utf-8",
    )


def pain_row(
    pain_item_id: str,
    source_url: str,
    workflow_stage: str = "deal sourcing",
    pain_type: str = "manual_workflow",
    evidence_strength: str = "strong",
    confidence: float = 0.86,
    title: str | None = None,
    result_domain: str | None = None,
    quote: str | None = None,
) -> dict[str, Any]:
    domain = result_domain or source_url.split("/")[2]
    return {
        "pain_item_id": pain_item_id,
        "candidate_id": f"cand_{pain_item_id}",
        "should_extract": True,
        "title": title or f"{workflow_stage} pain {pain_item_id}",
        "source_url": source_url,
        "result_domain": domain,
        "persona": "VC analyst",
        "workflow_stage": workflow_stage,
        "pain_type": pain_type,
        "job_to_be_done": f"Need to improve {workflow_stage}",
        "pain_description_zh": f"{workflow_stage} 中存在手工流程和信息分散问题 {pain_item_id}",
        "evidence_quote": quote or "We use spreadsheets and manual research across many tools.",
        "current_solution": "spreadsheet",
        "commercial_signal_type": "manual_labor_cost",
        "evidence_strength": evidence_strength,
        "confidence": confidence,
        "metadata": {
            "seed_id": "seed__001",
            "query_type": "manual_workflow",
            "raw_text_source": "full_page",
            "result_domain": domain,
        },
    }


def review_row(
    pain_item_id: str,
    action_decision: str = "pursue",
    true_pain: bool | None = True,
    commercial_potential: str = "medium",
) -> dict[str, Any]:
    return {
        "review_id": f"d4_review_{pain_item_id}",
        "pain_item_id": pain_item_id,
        "candidate_id": f"cand_{pain_item_id}",
        "source_url": "https://example.test/reviewed",
        "reviewer": "user",
        "true_pain": true_pain,
        "commercial_potential": commercial_potential,
        "evidence_quality": "strong",
        "action_decision": action_decision,
        "extraction_quality": "good",
        "error_labels": [],
        "created_at": "2026-06-17T00:00:00Z",
    }


def write_config(tmp_path: Path, pain_path: Path, reviews_path: Path) -> Path:
    config = tmp_path / "d5_config.yaml"
    config.write_text(
        f"""
demand_theme_grouping:
  input:
    d4_pain_items_path: {pain_path.as_posix()}
    d4_reviews_path: {reviews_path.as_posix()}
  output:
    deduped_pain_items_path: {(tmp_path / 'deduped.jsonl').as_posix()}
    source_groups_path: {(tmp_path / 'source_groups.jsonl').as_posix()}
    demand_themes_path: {(tmp_path / 'themes.jsonl').as_posix()}
    theme_review_queue_path: {(tmp_path / 'queue.jsonl').as_posix()}
    dedupe_report_path: {(tmp_path / 'dedupe.md').as_posix()}
    source_group_report_path: {(tmp_path / 'source_groups.md').as_posix()}
    demand_theme_report_path: {(tmp_path / 'themes.md').as_posix()}
    theme_review_queue_report_path: {(tmp_path / 'queue.md').as_posix()}
    d5_summary_report_path: {(tmp_path / 'summary.md').as_posix()}
  evidence_selection:
    include_strength:
      - strong
      - medium
""",
        encoding="utf-8",
    )
    return config
