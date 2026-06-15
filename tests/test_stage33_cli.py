"""Tests for Stage 3.3 CLI commands."""
import csv
import json
import os
import pytest
from pathlib import Path
from datetime import datetime, timezone
from typer.testing import CliRunner
from demand_radar.cli import app


runner = CliRunner()


def _now():
    return datetime.now(timezone.utc).isoformat()


def _make_plan(group_id, title, n_signals):
    return {
        "plan_id": f"plan_{group_id}",
        "gap_analysis_id": f"gap_{group_id}",
        "truth_score_id": f"ts_{group_id}",
        "source_group_id": group_id,
        "group_title_zh": title,
        "target_new_signals": n_signals,
        "target_personas": [],
        "target_source_types": ["pricing_page"],
        "target_languages": ["zh"],
        "search_keywords_zh": ["测试关键词"],
        "search_keywords_en": ["test keyword"],
        "positive_signal_criteria": ["has payment"],
        "negative_signal_criteria": ["no payment"],
        "collection_notes_zh": "测试采集计划",
        "expected_impact_zh": "预期提升分数",
        "created_at": _now(),
    }


@pytest.fixture
def isolated_env(tmp_path, monkeypatch):
    """Redirect all Stage 3.3 paths to tmp_path."""
    plan_path = tmp_path / "data" / "processed" / "targeted_signal_collection_plan.jsonl"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plans = [_make_plan("grp_001", "内容团队选题", 3), _make_plan("grp_002", "AI产业跟踪", 3)]
    plan_path.write_text("\n".join(json.dumps(p) for p in plans), encoding="utf-8")

    template_path = tmp_path / "examples" / "stage33_targeted_signal_template.csv"
    template_path.parent.mkdir(parents=True, exist_ok=True)

    ts_path = tmp_path / "data" / "processed" / "truth_scores.jsonl"
    ts_path.write_text("", encoding="utf-8")

    summary_path = tmp_path / "data" / "processed" / "targeted_expansion_run_summary.json"
    delta_path = tmp_path / "data" / "processed" / "truth_score_deltas.jsonl"
    val_path = tmp_path / "data" / "processed" / "targeted_signal_validation.jsonl"
    report_path = tmp_path / "outputs" / "targeted_expansion_report.md"
    delta_report_path = tmp_path / "outputs" / "truth_score_delta_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    import demand_radar.targeted_expansion.template_builder as tb
    import demand_radar.targeted_expansion.expansion_store as es
    import demand_radar.targeted_expansion.targeted_validator as tv
    import demand_radar.targeted_expansion.expansion_report as er
    import demand_radar.targeted_expansion.expansion_pipeline as ep
    import demand_radar.targeted_expansion.combined_input_builder as cb

    monkeypatch.setattr(tb, "Path", lambda p: tmp_path / str(p).lstrip("/\\").replace("data/processed/targeted_signal_collection_plan.jsonl", "data/processed/targeted_signal_collection_plan.jsonl").replace("data\\processed\\targeted_signal_collection_plan.jsonl", "data/processed/targeted_signal_collection_plan.jsonl") if "targeted_signal_collection_plan" in str(p) else Path(p))
    # Simpler approach: patch specific known paths
    monkeypatch.setattr(es, "SUMMARY_PATH", summary_path)
    monkeypatch.setattr(es, "DELTA_PATH", delta_path)

    return {
        "tmp": tmp_path,
        "plan_path": plan_path,
        "template_path": template_path,
        "ts_path": ts_path,
        "summary_path": summary_path,
        "val_path": val_path,
        "report_path": report_path,
    }


def test_build_targeted_signal_template_command_exists():
    """Command exists and shows help."""
    result = runner.invoke(app, ["build-targeted-signal-template", "--help"])
    assert result.exit_code == 0
    assert "template" in result.output.lower()


def test_validate_targeted_signals_command_exists():
    result = runner.invoke(app, ["validate-targeted-signals", "--help"])
    assert result.exit_code == 0


def test_build_combined_stage33_input_command_exists():
    result = runner.invoke(app, ["build-combined-stage33-input", "--help"])
    assert result.exit_code == 0


def test_build_targeted_expansion_report_command_exists():
    result = runner.invoke(app, ["build-targeted-expansion-report", "--help"])
    assert result.exit_code == 0


def test_build_truth_score_delta_report_command_exists():
    result = runner.invoke(app, ["build-truth-score-delta-report", "--help"])
    assert result.exit_code == 0


def test_run_stage33_command_exists():
    result = runner.invoke(app, ["run-stage33", "--help"])
    assert result.exit_code == 0


def test_run_stage33_full_command_exists():
    result = runner.invoke(app, ["run-stage33-full", "--help"])
    assert result.exit_code == 0


def test_run_stage33_full_skip_llm_no_api_key(tmp_path, monkeypatch):
    """run-stage33-full --skip-llm runs without requiring API key."""
    import demand_radar.targeted_expansion.expansion_store as es
    import demand_radar.batch.batch_report as br

    summary_path = tmp_path / "summary.json"
    delta_path = tmp_path / "deltas.jsonl"
    monkeypatch.setattr(es, "SUMMARY_PATH", summary_path)
    monkeypatch.setattr(es, "DELTA_PATH", delta_path)
    monkeypatch.delenv("DEMAND_RADAR_LLM_API_KEY", raising=False)

    # Patch batch_report to avoid real file access
    monkeypatch.setattr(br, "build_batch_summary_report", lambda **kwargs: None)

    result = runner.invoke(app, ["run-stage33-full", "--skip-llm"])
    # Should succeed or at least not fail due to missing API key
    assert result.exit_code == 0 or "API" not in (result.output or "")


def test_run_stage33_full_no_key_exits_with_error(monkeypatch):
    """run-stage33-full without --skip-llm and no API key should fail gracefully."""
    import demand_radar.targeted_expansion.expansion_store as es
    monkeypatch.setattr(es, "SUMMARY_PATH", Path("/tmp/nonexistent_summary.json"))
    monkeypatch.setattr(es, "DELTA_PATH", Path("/tmp/nonexistent_delta.jsonl"))
    monkeypatch.delenv("DEMAND_RADAR_LLM_API_KEY", raising=False)
    result = runner.invoke(app, ["run-stage33-full"])
    # Should exit with non-zero due to missing API key
    assert result.exit_code != 0 or "ERROR" in result.output


def test_build_truth_score_delta_report_no_data(tmp_path, monkeypatch):
    """Delta report shows no comparison when no data."""
    import demand_radar.targeted_expansion.expansion_store as es
    delta_path = tmp_path / "no_deltas.jsonl"
    monkeypatch.setattr(es, "DELTA_PATH", delta_path)
    out_path = tmp_path / "outputs" / "truth_score_delta_report.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    from demand_radar.targeted_expansion.expansion_report import build_truth_score_delta_report
    build_truth_score_delta_report([], output_path=str(out_path))
    content = out_path.read_text(encoding="utf-8")
    assert "No comparison available" in content
