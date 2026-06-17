"""Typer CLI for Stage 1 Demand Radar."""

from __future__ import annotations

import os as _os
from pathlib import Path as _Path

_env_file = _Path(__file__).parent.parent.parent / ".env"
if _env_file.exists():
    with open(_env_file, encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                _os.environ.setdefault(_k, _v)

import subprocess
import sys
from pathlib import Path
from typing import Annotated

import typer

from demand_radar.batch.batch_report import build_batch_summary_report
from demand_radar.calibration.calibration_review import append_calibration_review
from demand_radar.cleaning.text_cleaner import normalize_signals
from demand_radar.clustering.cluster_report import build_cluster_report
from demand_radar.clustering.demand_clusterer import run_demand_clustering
from demand_radar.clustering.merge_report import build_merge_report, build_reviewed_groups_report
from demand_radar.clustering.merge_store import build_reviewed_cluster_groups
from demand_radar.clustering.merge_suggester import suggest_cluster_merges
from demand_radar.config.load_config import load_configs
from demand_radar.intake.manual_import import import_file
from demand_radar.loops.pain_extraction_loop import run_pain_extraction
from demand_radar.reporting.calibration_report import build_calibration_report
from demand_radar.reporting.pain_points_report import build_pain_points_report
from demand_radar.semantic_merge.semantic_merge_judge import run_semantic_merge_judge
from demand_radar.semantic_merge.semantic_merge_report import (
    build_ai_reviewed_groups_report,
    build_human_exception_report,
    build_semantic_merge_report,
)
from demand_radar.semantic_merge.semantic_merge_store import build_ai_reviewed_cluster_groups
from demand_radar.state.raw_store import ensure_jsonl_file
from demand_radar.semantic_merge.llm_judge_runner import (
    build_llm_ai_reviewed_cluster_groups,
    run_llm_semantic_merge_judge,
)
from demand_radar.semantic_merge.llm_comparison_report import build_semantic_merge_comparison_report
from demand_radar.semantic_merge.llm_reports import (
    build_llm_ai_reviewed_groups_report,
    build_llm_human_exception_report,
    build_llm_semantic_merge_report,
)



from demand_radar.truth_scoring.truth_pipeline import run_truth_scoring
from demand_radar.truth_scoring.truth_report import (
    build_top_truth_candidates_report,
    build_truth_scoring_report,
)
from demand_radar.truth_scoring.truth_store import load_truth_scores

from demand_radar.evidence_gap.evidence_gap_analyzer import analyze_gaps
from demand_radar.evidence_gap.evidence_gap_report import (
    build_evidence_gap_report,
    build_targeted_signal_plan_report,
)
from demand_radar.evidence_gap.evidence_gap_store import (
    load_gap_analysis,
    write_gap_analysis,
    write_collection_plans,
)
from demand_radar.evidence_gap.signal_collection_plan import build_collection_plans

from demand_radar.targeted_expansion.template_builder import build_template
from demand_radar.targeted_expansion.targeted_validator import validate_targeted_signals, load_validations
from demand_radar.targeted_expansion.combined_input_builder import build_combined_input
from demand_radar.targeted_expansion.expansion_pipeline import run_stage33 as _run_stage33_pipeline
from demand_radar.targeted_expansion.expansion_report import (
    build_targeted_expansion_report,
    build_truth_score_delta_report,
)
from demand_radar.targeted_expansion.expansion_store import (
    load_expansion_summary, load_truth_score_deltas, write_expansion_summary,
)
from demand_radar.mvp_d.evidence_consolidator import consolidate_evidence
from demand_radar.mvp_d.expansion_extraction import run_expansion_extraction
from demand_radar.mvp_d.mvp_d_pipeline import build_mvp_d_summary_from_stored, run_mvp_d
from demand_radar.mvp_d.query_generator import generate_queries
from demand_radar.mvp_d.seed_selector import select_seeds
from demand_radar.mvp_d.seeded_acquisition import run_seeded_acquisition
from demand_radar.mvp_d.theme_grouping import build_demand_themes
from demand_radar.mvp_d2.calibrated_expansion_runner import run_calibrated_expansion
from demand_radar.mvp_d2.calibrated_query_generator import build_calibrated_query_plan
from demand_radar.mvp_d2.d2_comparison import compare_expansion_v1_v2
from demand_radar.mvp_d2.mvp_d2_pipeline import build_mvp_d2_summary_from_stored, run_mvp_d2
from demand_radar.mvp_d2.reject_diagnostics_runner import run_reject_diagnostics
from demand_radar.mvp_d2.source_quality_analyzer import analyze_source_quality
app = typer.Typer(help="Domain-Bounded Demand Radar Stage 1 CLI.")
calibration_review_app = typer.Typer(help="Human calibration review commands.")
app.add_typer(calibration_review_app, name="calibration-review")

RUNTIME_FILES = [
    Path("data/raw/raw_signals.jsonl"),
    Path("data/processed/normalized_signals.jsonl"),
    Path("data/processed/pain_points.jsonl"),
    Path("data/processed/calibration_reviews.jsonl"),
    Path("data/processed/demand_clusters.jsonl"),
    Path("data/processed/cluster_reviews.jsonl"),
    Path("data/processed/cluster_merge_candidates.jsonl"),
    Path("data/processed/cluster_group_reviews.jsonl"),
    Path("data/processed/reviewed_cluster_groups.jsonl"),
    Path("data/processed/semantic_merge_judgments.jsonl"),
    Path("data/processed/ai_reviewed_cluster_groups.jsonl"),
    Path("data/processed/human_exception_queue.jsonl"),
    Path("data/processed/semantic_merge_human_audits.jsonl"),
    Path("data/quarantine/invalid_outputs.jsonl"),
    Path("data/quarantine/invalid_clusters.jsonl"),
    Path("data/quarantine/invalid_merge_candidates.jsonl"),
    Path("data/quarantine/invalid_reviewed_groups.jsonl"),
    Path("data/quarantine/invalid_ai_reviewed_groups.jsonl"),
    Path("outputs/pain_points_report.md"),
    Path("outputs/calibration_report.md"),
    Path("outputs/demand_clusters_report.md"),
    Path("outputs/cluster_merge_suggestions.md"),
    Path("outputs/reviewed_cluster_groups_report.md"),
    Path("outputs/semantic_merge_judgment_report.md"),
    Path("outputs/ai_reviewed_cluster_groups_report.md"),
    Path("outputs/human_exception_queue_report.md"),
    Path("outputs/batch_summary_report.md"),
    Path("outputs/batch_quality_matrix.csv"),
    Path("outputs/run_summary.json"),
]


STAGE2_REGENERATED_FILES = [
    Path("data/raw/raw_signals.jsonl"),
    Path("data/processed/normalized_signals.jsonl"),
    Path("data/processed/pain_points.jsonl"),
    Path("data/processed/demand_clusters.jsonl"),
    Path("data/processed/cluster_merge_candidates.jsonl"),
    Path("data/processed/reviewed_cluster_groups.jsonl"),
    Path("data/processed/semantic_merge_judgments.jsonl"),
    Path("data/processed/ai_reviewed_cluster_groups.jsonl"),
    Path("data/processed/human_exception_queue.jsonl"),
    Path("data/quarantine/invalid_outputs.jsonl"),
    Path("data/quarantine/invalid_clusters.jsonl"),
    Path("data/quarantine/invalid_merge_candidates.jsonl"),
    Path("data/quarantine/invalid_reviewed_groups.jsonl"),
    Path("data/quarantine/invalid_ai_reviewed_groups.jsonl"),
    Path("outputs/pain_points_report.md"),
    Path("outputs/calibration_report.md"),
    Path("outputs/demand_clusters_report.md"),
    Path("outputs/cluster_merge_suggestions.md"),
    Path("outputs/reviewed_cluster_groups_report.md"),
    Path("outputs/semantic_merge_judgment_report.md"),
    Path("outputs/ai_reviewed_cluster_groups_report.md"),
    Path("outputs/human_exception_queue_report.md"),
    Path("outputs/batch_summary_report.md"),
    Path("outputs/batch_quality_matrix.csv"),
    Path("outputs/run_summary.json"),
]


@app.command()
def init(reset: Annotated[bool, typer.Option(help="Clear Stage 1 runtime files.")] = False) -> None:
    """Create required directories and empty runtime files."""

    for directory in ["configs", "data/raw", "data/processed", "data/quarantine", "outputs", "prompts", "examples"]:
        Path(directory).mkdir(parents=True, exist_ok=True)
    for path in RUNTIME_FILES:
        if reset or not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("", encoding="utf-8")
    ensure_jsonl_file("data/raw/raw_signals.jsonl")
    configs = load_configs("configs")
    typer.echo(f"Initialized Stage 1 workspace. Loaded configs: {', '.join(configs.keys())}")


@app.command("import")
def import_command(
    file: Annotated[Path, typer.Option("--file", exists=True, readable=True, help="CSV or JSONL file to import.")],
) -> None:
    """Import manual CSV or JSONL signals into Raw State."""

    imported = import_file(file)
    typer.echo(f"Imported {len(imported)} raw signals -> data/raw/raw_signals.jsonl")


@app.command()
def normalize() -> None:
    """Normalize Raw State into Working State."""

    normalized = normalize_signals()
    typer.echo(f"Normalized {len(normalized)} signals -> data/processed/normalized_signals.jsonl")


@app.command("extract-pain")
def extract_pain() -> None:
    """Run the Stage 1 Pain Extraction Loop."""

    pain_points = run_pain_extraction()
    typer.echo(f"Extracted {len(pain_points)} valid pain points -> data/processed/pain_points.jsonl")


@app.command("build-pain-report")
def build_pain_report() -> None:
    """Build the Stage 1 pain points report."""

    summary = build_pain_points_report()
    typer.echo(
        "Built pain report -> outputs/pain_points_report.md "
        f"(pain_points={summary.pain_points}, quarantine={summary.quarantined_items})"
    )


@app.command("build-calibration-report")
def build_calibration_report_command() -> None:
    """Build the Stage 1.5 extraction calibration report."""

    summary = build_calibration_report()
    typer.echo(
        "Built calibration report -> outputs/calibration_report.md "
        f"(reviews={summary.calibration_reviews}, pain_points={summary.pain_points}, "
        f"quarantine={summary.quarantined_items})"
    )


@app.command("run-cluster")
def run_cluster() -> None:
    """Run the Stage 2 Demand Clustering Loop from current pain points."""

    clusters = run_demand_clustering()
    typer.echo(f"Generated {len(clusters)} demand clusters -> data/processed/demand_clusters.jsonl")


@app.command("build-cluster-report")
def build_cluster_report_command() -> None:
    """Build the Stage 2 demand clusters report."""

    summary = build_cluster_report()
    typer.echo(
        "Built cluster report -> outputs/demand_clusters_report.md "
        f"(clusters={summary.demand_clusters}, singleton={summary.singleton_clusters}, "
        f"reviews={summary.cluster_reviews})"
    )


@app.command("suggest-merges")
def suggest_merges() -> None:
    """Generate Stage 2.5 cluster merge candidates from current demand clusters."""

    candidates = suggest_cluster_merges()
    typer.echo(
        "Generated merge candidates -> data/processed/cluster_merge_candidates.jsonl "
        f"(candidates={len(candidates)})"
    )


@app.command("build-merge-report")
def build_merge_report_command() -> None:
    """Build the Stage 2.5 merge suggestions report."""

    summary = build_merge_report()
    typer.echo(
        "Built merge suggestions report -> outputs/cluster_merge_suggestions.md "
        f"(candidates={summary.merge_candidates}, reviewed={summary.reviewed_candidates})"
    )


@app.command("build-reviewed-groups")
def build_reviewed_groups() -> None:
    """Build reviewed cluster groups from confirmed merge reviews."""

    groups = build_reviewed_cluster_groups()
    typer.echo(
        "Built reviewed cluster groups -> data/processed/reviewed_cluster_groups.jsonl "
        f"(groups={len(groups)})"
    )


@app.command("build-reviewed-groups-report")
def build_reviewed_groups_report_command() -> None:
    """Build the reviewed cluster groups report."""

    summary = build_reviewed_groups_report()
    typer.echo(
        "Built reviewed groups report -> outputs/reviewed_cluster_groups_report.md "
        f"(groups={summary.reviewed_groups}, clusters={summary.included_clusters})"
    )


@app.command("build-batch-summary")
def build_batch_summary_command() -> None:
    """Build the Stage 2.6 batch summary report."""

    summary = build_batch_summary_report()
    typer.echo(
        "Built batch summary report -> outputs/batch_summary_report.md "
        f"(batches={len(summary.batches)}, ready_for_truth_scoring="
        f"{summary.readiness.ready_for_truth_scoring})"
    )


@app.command("semantic-merge-judge")
def semantic_merge_judge_command() -> None:
    """Run the Stage 2.7 AI semantic merge judge from current merge candidates."""

    judgments = run_semantic_merge_judge()
    auto_confirmed = sum(1 for judgment in judgments if judgment.auto_action == "auto_confirm")
    auto_rejected = sum(1 for judgment in judgments if judgment.auto_action == "auto_reject")
    human_exceptions = sum(1 for judgment in judgments if judgment.auto_action == "human_exception")
    typer.echo(
        "Built semantic merge judgments -> data/processed/semantic_merge_judgments.jsonl "
        f"(judgments={len(judgments)}, auto_confirmed={auto_confirmed}, "
        f"auto_rejected={auto_rejected}, human_exceptions={human_exceptions})"
    )


@app.command("build-ai-reviewed-groups")
def build_ai_reviewed_groups_command() -> None:
    """Build AI reviewed cluster groups from auto-confirmed semantic judgments."""

    groups = build_ai_reviewed_cluster_groups()
    summary = build_ai_reviewed_groups_report()
    typer.echo(
        "Built AI reviewed cluster groups -> data/processed/ai_reviewed_cluster_groups.jsonl "
        f"(groups={len(groups)}, clusters={summary.included_clusters})"
    )


@app.command("build-semantic-merge-report")
def build_semantic_merge_report_command() -> None:
    """Build the Stage 2.7 semantic merge judgment report."""

    summary = build_semantic_merge_report()
    typer.echo(
        "Built semantic merge judgment report -> outputs/semantic_merge_judgment_report.md "
        f"(judgments={summary.judgments}, auto_confirmed={summary.auto_confirmed}, "
        f"human_exceptions={summary.human_exceptions})"
    )


@app.command("build-human-exception-report")
def build_human_exception_report_command() -> None:
    """Build the Stage 2.7 human exception queue report."""

    summary = build_human_exception_report()
    typer.echo(
        "Built human exception queue report -> outputs/human_exception_queue_report.md "
        f"(exceptions={summary.exceptions}, high={summary.high_priority})"
    )


@app.command("run-stage1")
def run_stage1(
    input: Annotated[Path, typer.Option("--input", exists=True, readable=True, help="CSV or JSONL input file.")],
) -> None:
    """Run init, import, normalize, extract-pain, and build-pain-report."""

    init(reset=True)
    imported = import_file(input)
    typer.echo(f"Imported {len(imported)} raw signals -> data/raw/raw_signals.jsonl")
    normalized = normalize_signals()
    typer.echo(f"Normalized {len(normalized)} signals -> data/processed/normalized_signals.jsonl")
    pain_points = run_pain_extraction()
    typer.echo(f"Extracted {len(pain_points)} valid pain points -> data/processed/pain_points.jsonl")
    summary = build_pain_points_report()
    typer.echo(
        "Built pain report -> outputs/pain_points_report.md "
        f"(raw={summary.raw_signals}, normalized={summary.normalized_signals}, "
        f"pain_points={summary.pain_points}, quarantine={summary.quarantined_items})"
    )


@app.command("run-calibration")
def run_calibration(
    input: Annotated[Path, typer.Option("--input", exists=True, readable=True, help="CSV or JSONL input file.")],
) -> None:
    """Run the Stage 1.5 real-signal calibration pipeline."""

    init(reset=True)
    imported = import_file(input)
    typer.echo(f"Imported {len(imported)} raw signals -> data/raw/raw_signals.jsonl")
    normalized = normalize_signals()
    typer.echo(f"Normalized {len(normalized)} signals -> data/processed/normalized_signals.jsonl")
    pain_points = run_pain_extraction()
    typer.echo(f"Extracted {len(pain_points)} valid pain points -> data/processed/pain_points.jsonl")
    pain_summary = build_pain_points_report()
    typer.echo(
        "Built pain report -> outputs/pain_points_report.md "
        f"(raw={pain_summary.raw_signals}, normalized={pain_summary.normalized_signals}, "
        f"pain_points={pain_summary.pain_points}, quarantine={pain_summary.quarantined_items})"
    )
    calibration_summary = build_calibration_report()
    typer.echo(
        "Built calibration report -> outputs/calibration_report.md "
        f"(reviews={calibration_summary.calibration_reviews})"
    )


@app.command("run-stage2")
def run_stage2(
    input: Annotated[
        Path | None,
        typer.Option("--input", exists=True, readable=True, help="Optional CSV or JSONL input file."),
    ] = None,
) -> None:
    """Run Stage 2 clustering, optionally rebuilding pain points from input first."""

    init(reset=False)
    if input is not None:
        _clear_regenerated_stage2_files()
        imported = import_file(input)
        typer.echo(f"Imported {len(imported)} raw signals -> data/raw/raw_signals.jsonl")
        normalized = normalize_signals()
        typer.echo(f"Normalized {len(normalized)} signals -> data/processed/normalized_signals.jsonl")
        pain_points = run_pain_extraction()
        typer.echo(f"Extracted {len(pain_points)} valid pain points -> data/processed/pain_points.jsonl")
        pain_summary = build_pain_points_report()
        typer.echo(
            "Built pain report -> outputs/pain_points_report.md "
            f"(raw={pain_summary.raw_signals}, normalized={pain_summary.normalized_signals}, "
            f"pain_points={pain_summary.pain_points}, quarantine={pain_summary.quarantined_items})"
        )
        calibration_summary = build_calibration_report()
        typer.echo(
            "Built calibration report -> outputs/calibration_report.md "
            f"(reviews={calibration_summary.calibration_reviews})"
        )

    clusters = run_demand_clustering()
    typer.echo(f"Generated {len(clusters)} demand clusters -> data/processed/demand_clusters.jsonl")
    cluster_summary = build_cluster_report()
    typer.echo(
        "Built cluster report -> outputs/demand_clusters_report.md "
        f"(pain_points={cluster_summary.pain_points}, clusters={cluster_summary.demand_clusters}, "
        f"singleton={cluster_summary.singleton_clusters}, invalid={cluster_summary.invalid_clusters}, "
        f"cluster_reviews={cluster_summary.cluster_reviews})"
    )


@app.command("run-stage25")
def run_stage25(
    input: Annotated[
        Path | None,
        typer.Option("--input", exists=True, readable=True, help="Optional CSV or JSONL input file."),
    ] = None,
) -> None:
    """Run Stage 2.5 merge suggestions and reviewed group report generation."""

    init(reset=False)
    if input is not None:
        _run_stage2_core(input)

    candidates = suggest_cluster_merges()
    typer.echo(
        "Generated merge candidates -> data/processed/cluster_merge_candidates.jsonl "
        f"(candidates={len(candidates)})"
    )
    merge_summary = build_merge_report()
    typer.echo(
        "Built merge suggestions report -> outputs/cluster_merge_suggestions.md "
        f"(candidates={merge_summary.merge_candidates}, reviewed={merge_summary.reviewed_candidates}, "
        f"confirmed={merge_summary.confirmed_merges})"
    )
    groups = build_reviewed_cluster_groups()
    typer.echo(
        "Built reviewed cluster groups -> data/processed/reviewed_cluster_groups.jsonl "
        f"(groups={len(groups)})"
    )
    groups_summary = build_reviewed_groups_report()
    typer.echo(
        "Built reviewed groups report -> outputs/reviewed_cluster_groups_report.md "
        f"(groups={groups_summary.reviewed_groups}, clusters={groups_summary.included_clusters})"
    )


@app.command("run-stage26")
def run_stage26(
    input: Annotated[
        Path,
        typer.Option("--input", exists=True, readable=True, help="CSV or JSONL input file."),
    ] = Path("examples/real_signal_samples_stage26.csv"),
) -> None:
    """Run Stage 2.6 batch radar pipeline from expanded real-signal samples."""

    init(reset=False)
    _run_stage2_core(input)

    candidates = suggest_cluster_merges()
    typer.echo(
        "Generated merge candidates -> data/processed/cluster_merge_candidates.jsonl "
        f"(candidates={len(candidates)})"
    )
    merge_summary = build_merge_report()
    typer.echo(
        "Built merge suggestions report -> outputs/cluster_merge_suggestions.md "
        f"(candidates={merge_summary.merge_candidates}, reviewed={merge_summary.reviewed_candidates}, "
        f"confirmed={merge_summary.confirmed_merges})"
    )
    groups = build_reviewed_cluster_groups()
    typer.echo(
        "Built reviewed cluster groups -> data/processed/reviewed_cluster_groups.jsonl "
        f"(groups={len(groups)})"
    )
    groups_summary = build_reviewed_groups_report()
    typer.echo(
        "Built reviewed groups report -> outputs/reviewed_cluster_groups_report.md "
        f"(groups={groups_summary.reviewed_groups}, clusters={groups_summary.included_clusters})"
    )
    batch_summary = build_batch_summary_report()
    typer.echo(
        "Built batch summary report -> outputs/batch_summary_report.md "
        f"(batches={len(batch_summary.batches)}, ready_for_truth_scoring="
        f"{batch_summary.readiness.ready_for_truth_scoring})"
    )


@app.command("run-stage27")
def run_stage27(
    input: Annotated[
        Path | None,
        typer.Option("--input", exists=True, readable=True, help="Optional CSV or JSONL input file."),
    ] = None,
) -> None:
    """Run Stage 2.7 semantic merge judge and AI reviewed group generation."""

    init(reset=False)
    if input is not None:
        _run_stage2_core(input)
        candidates = suggest_cluster_merges()
        typer.echo(
            "Generated merge candidates -> data/processed/cluster_merge_candidates.jsonl "
            f"(candidates={len(candidates)})"
        )
        merge_summary = build_merge_report()
        typer.echo(
            "Built merge suggestions report -> outputs/cluster_merge_suggestions.md "
            f"(candidates={merge_summary.merge_candidates}, reviewed={merge_summary.reviewed_candidates}, "
            f"confirmed={merge_summary.confirmed_merges})"
        )

    judgments = run_semantic_merge_judge()
    auto_confirmed = sum(1 for judgment in judgments if judgment.auto_action == "auto_confirm")
    auto_rejected = sum(1 for judgment in judgments if judgment.auto_action == "auto_reject")
    human_exceptions = sum(1 for judgment in judgments if judgment.auto_action == "human_exception")
    typer.echo(
        "Built semantic merge judgments -> data/processed/semantic_merge_judgments.jsonl "
        f"(judgments={len(judgments)}, auto_confirmed={auto_confirmed}, "
        f"auto_rejected={auto_rejected}, human_exceptions={human_exceptions})"
    )
    semantic_summary = build_semantic_merge_report()
    typer.echo(
        "Built semantic merge judgment report -> outputs/semantic_merge_judgment_report.md "
        f"(human_exception_rate={semantic_summary.human_exception_rate})"
    )
    exception_summary = build_human_exception_report()
    typer.echo(
        "Built human exception queue report -> outputs/human_exception_queue_report.md "
        f"(exceptions={exception_summary.exceptions})"
    )
    groups = build_ai_reviewed_cluster_groups()
    groups_summary = build_ai_reviewed_groups_report()
    typer.echo(
        "Built AI reviewed cluster groups -> data/processed/ai_reviewed_cluster_groups.jsonl "
        f"(groups={len(groups)}, clusters={groups_summary.included_clusters})"
    )
    batch_summary = build_batch_summary_report()
    typer.echo(
        "Built batch summary report -> outputs/batch_summary_report.md "
        f"(batches={len(batch_summary.batches)}, ready_for_truth_scoring="
        f"{batch_summary.readiness.ready_for_truth_scoring})"
    )



@app.command("run-stage28")
def run_stage28(
    input: Annotated[
        Path | None,
        typer.Option("--input", exists=True, readable=True, help="Optional CSV or JSONL input file."),
    ] = None,
) -> None:
    """Run Stage 2.8: full pipeline including AI semantic merge as main flow."""

    init(reset=False)
    if input is not None:
        _run_stage2_core(input)
        candidates = suggest_cluster_merges()
        typer.echo(
            "Generated merge candidates -> data/processed/cluster_merge_candidates.jsonl "
            f"(candidates={len(candidates)})"
        )
        merge_summary = build_merge_report()
        typer.echo(
            "Built merge suggestions report -> outputs/cluster_merge_suggestions.md "
            f"(candidates={merge_summary.merge_candidates}, reviewed={merge_summary.reviewed_candidates}, "
            f"confirmed={merge_summary.confirmed_merges})"
        )

    judgments = run_semantic_merge_judge()
    auto_confirmed = sum(1 for j in judgments if j.auto_action == "auto_confirm")
    auto_rejected = sum(1 for j in judgments if j.auto_action == "auto_reject")
    human_exceptions = sum(1 for j in judgments if j.auto_action == "human_exception")
    typer.echo(
        "Built semantic merge judgments -> data/processed/semantic_merge_judgments.jsonl "
        f"(judgments={len(judgments)}, auto_confirmed={auto_confirmed}, "
        f"auto_rejected={auto_rejected}, human_exceptions={human_exceptions})"
    )
    semantic_summary = build_semantic_merge_report()
    typer.echo(
        "Built semantic merge judgment report -> outputs/semantic_merge_judgment_report.md "
        f"(human_exception_rate={semantic_summary.human_exception_rate})"
    )
    exception_summary = build_human_exception_report()
    typer.echo(
        "Built human exception queue report -> outputs/human_exception_queue_report.md "
        f"(exceptions={exception_summary.exceptions})"
    )
    groups = build_ai_reviewed_cluster_groups()
    groups_summary = build_ai_reviewed_groups_report()
    typer.echo(
        "Built AI reviewed cluster groups -> data/processed/ai_reviewed_cluster_groups.jsonl "
        f"(groups={len(groups)}, clusters={groups_summary.included_clusters})"
    )
    batch_summary = build_batch_summary_report()
    typer.echo(
        "Built batch summary report -> outputs/batch_summary_report.md "
        f"(batches={len(batch_summary.batches)}, ready_for_truth_scoring="
        f"{batch_summary.readiness.ready_for_truth_scoring})"
    )
    typer.echo(
        f"Stage 2.8 complete — AI 主流程已处理 {auto_confirmed} 条自动确认、"
        f"{auto_rejected} 条自动拒绝，{human_exceptions} 条进入人工异常队列。"
    )


@app.command("select-expansion-seeds")
def select_expansion_seeds_command(
    domain: Annotated[str, typer.Option("--domain")] = "ai_investment_tracking",
    max_seeds: Annotated[int | None, typer.Option("--max-seeds")] = None,
    max_queries: Annotated[int | None, typer.Option("--max-queries")] = None,
    max_results: Annotated[int | None, typer.Option("--max-results")] = None,
    use_cache: Annotated[bool, typer.Option("--use-cache/--no-cache")] = True,
) -> None:
    """Select reviewed pain seeds for MVP-D expansion."""
    seeds, summary = select_seeds(max_seeds_override=max_seeds)
    typer.echo(
        "Built MVP-D seed profiles -> data/processed/mvp_d/seed_profiles.jsonl "
        f"(seeds={len(seeds)}, eligible={summary.eligible_seeds}, optional={summary.optional_seeds})"
    )


@app.command("build-seeded-query-plan")
def build_seeded_query_plan_command(
    domain: Annotated[str, typer.Option("--domain")] = "ai_investment_tracking",
    max_seeds: Annotated[int | None, typer.Option("--max-seeds")] = None,
    max_queries: Annotated[int | None, typer.Option("--max-queries")] = None,
    max_results: Annotated[int | None, typer.Option("--max-results")] = None,
    use_cache: Annotated[bool, typer.Option("--use-cache/--no-cache")] = True,
) -> None:
    """Build targeted query plan from MVP-D seeds."""
    from demand_radar.mvp_d.seed_selector import select_seeds
    seeds, _ = select_seeds(max_seeds_override=max_seeds)
    queries = generate_queries(seeds, max_queries_total=max_queries)
    typer.echo(
        "Built MVP-D query plan -> data/processed/mvp_d/seeded_query_plan.jsonl "
        f"(queries={len(queries)})"
    )


@app.command("run-seeded-acquisition")
def run_seeded_acquisition_command(
    domain: Annotated[str, typer.Option("--domain")] = "ai_investment_tracking",
    max_seeds: Annotated[int | None, typer.Option("--max-seeds")] = None,
    max_queries: Annotated[int | None, typer.Option("--max-queries")] = None,
    max_results: Annotated[int | None, typer.Option("--max-results")] = None,
    use_cache: Annotated[bool, typer.Option("--use-cache/--no-cache")] = True,
) -> None:
    """Run MVP-D seeded acquisition with existing connectors."""
    candidates, summary = run_seeded_acquisition(max_queries=max_queries, max_results=max_results)
    typer.echo(
        "Built MVP-D acquisition candidates -> data/processed/mvp_d/expansion_evidence_candidates.jsonl "
        f"(candidates={len(candidates)}, allowed={summary['allowed_by_gate']}, blocked={summary['blocked_by_gate']})"
    )


@app.command("run-expansion-extraction")
def run_expansion_extraction_command(
    domain: Annotated[str, typer.Option("--domain")] = "ai_investment_tracking",
    max_seeds: Annotated[int | None, typer.Option("--max-seeds")] = None,
    max_queries: Annotated[int | None, typer.Option("--max-queries")] = None,
    max_results: Annotated[int | None, typer.Option("--max-results")] = None,
    use_cache: Annotated[bool, typer.Option("--use-cache/--no-cache")] = True,
) -> None:
    """Run MVP-D domain relevance + pain extraction on expansion candidates."""
    relevance_rows, pain_rows, summary = run_expansion_extraction(max_items=max_results, use_cache=use_cache)
    typer.echo(
        "Built MVP-D extraction outputs -> data/processed/mvp_d/expansion_pain_items.jsonl "
        f"(selected={summary['selected_for_llm']}, should_extract_true={summary['should_extract_true']})"
    )


@app.command("build-demand-themes")
def build_demand_themes_command(
    domain: Annotated[str, typer.Option("--domain")] = "ai_investment_tracking",
    max_seeds: Annotated[int | None, typer.Option("--max-seeds")] = None,
    max_queries: Annotated[int | None, typer.Option("--max-queries")] = None,
    max_results: Annotated[int | None, typer.Option("--max-results")] = None,
    use_cache: Annotated[bool, typer.Option("--use-cache/--no-cache")] = True,
) -> None:
    """Build lightweight demand themes from MVP-D evidence consolidation."""
    consolidate_evidence()
    themes = build_demand_themes(
        Path("data/processed/mvp_d/seed_profiles.jsonl"),
        Path("data/processed/mvp_d/seed_evidence_consolidation.jsonl"),
        Path("data/processed/mvp_d/consolidated_evidence_themes.jsonl"),
        Path("outputs/mvp_d/demand_theme_grouping_report.md"),
    )
    typer.echo(
        "Built MVP-D demand themes -> data/processed/mvp_d/consolidated_evidence_themes.jsonl "
        f"(themes={len(themes)})"
    )


@app.command("build-mvp-d-report")
def build_mvp_d_report_command(
    domain: Annotated[str, typer.Option("--domain")] = "ai_investment_tracking",
    max_seeds: Annotated[int | None, typer.Option("--max-seeds")] = None,
    max_queries: Annotated[int | None, typer.Option("--max-queries")] = None,
    max_results: Annotated[int | None, typer.Option("--max-results")] = None,
    use_cache: Annotated[bool, typer.Option("--use-cache/--no-cache")] = True,
) -> None:
    """Build the MVP-D summary report from stored outputs."""
    summary = build_mvp_d_summary_from_stored(domain_id=domain)
    typer.echo(
        "Built MVP-D summary -> outputs/mvp_d/mvp_d_summary_report.md "
        f"(engineering={summary.engineering_acceptance}, product={summary.product_acceptance})"
    )


@app.command("run-mvp-d-llm-expansion")
def run_mvp_d_llm_expansion_command(
    domain: Annotated[str, typer.Option("--domain")] = "ai_investment_tracking",
    max_results: Annotated[int | None, typer.Option("--max-results")] = None,
    use_cache: Annotated[bool, typer.Option("--use-cache/--no-cache")] = True,
) -> None:
    """Run only the MVP-D LLM expansion pass from stored candidates."""
    _, pain_rows, extraction_summary = run_expansion_extraction(max_items=max_results, use_cache=use_cache)
    consolidate_evidence()
    themes = build_demand_themes(
        Path("data/processed/mvp_d/seed_profiles.jsonl"),
        Path("data/processed/mvp_d/seed_evidence_consolidation.jsonl"),
        Path("data/processed/mvp_d/consolidated_evidence_themes.jsonl"),
        Path("outputs/mvp_d/demand_theme_grouping_report.md"),
    )
    summary = build_mvp_d_summary_from_stored(domain_id=domain)
    typer.echo(
        "MVP-D LLM expansion complete -> outputs/mvp_d/mvp_d_llm_expansion_pass_report.md "
        f"(real_llm_run={str(extraction_summary['real_llm_run']).lower()}, "
        f"selected={extraction_summary['selected_for_llm']}, "
        f"processed={extraction_summary['processed']}, "
        f"should_extract_true={extraction_summary['should_extract_true']}, "
        f"themes={len(themes)}, engineering={summary.engineering_acceptance}, "
        f"product={summary.product_acceptance})"
    )


@app.command("run-mvp-d")
def run_mvp_d_command(
    domain: Annotated[str, typer.Option("--domain")] = "ai_investment_tracking",
    max_seeds: Annotated[int | None, typer.Option("--max-seeds")] = None,
    max_queries: Annotated[int | None, typer.Option("--max-queries")] = None,
    max_results: Annotated[int | None, typer.Option("--max-results")] = None,
    use_cache: Annotated[bool, typer.Option("--use-cache/--no-cache")] = True,
) -> None:
    """Run MVP-D seeded evidence expansion end-to-end."""
    summary = run_mvp_d(
        domain_id=domain,
        use_cache=use_cache,
        max_seeds=max_seeds,
        max_queries=max_queries,
        max_results=max_results,
    )
    typer.echo(
        "MVP-D complete -> outputs/mvp_d/mvp_d_summary_report.md "
        f"(seeds={summary.eligible_seeds}, queries={summary.total_queries}, "
        f"candidates={summary.unique_new_signals}, themes={summary.themes}, "
        f"engineering={summary.engineering_acceptance}, product={summary.product_acceptance})"
    )


@app.command("diagnose-expansion-rejects")
def diagnose_expansion_rejects_command(
    domain: Annotated[str, typer.Option("--domain")] = "ai_investment_tracking",
    max_queries: Annotated[int | None, typer.Option("--max-queries")] = None,
    max_results: Annotated[int | None, typer.Option("--max-results")] = None,
    use_cache: Annotated[bool, typer.Option("--use-cache/--no-cache")] = True,
    skip_pilot: Annotated[bool, typer.Option("--skip-pilot")] = False,
) -> None:
    """Diagnose MVP-D rejected expansion candidates."""
    diagnostics, summary = run_reject_diagnostics()
    _, source_summary = analyze_source_quality()
    typer.echo(
        "Built MVP-D2 reject diagnostics -> data/processed/mvp_d2/reject_diagnostics.jsonl "
        f"(total_rejected={summary['total_rejected']}, by_category={summary['by_reject_category']})"
    )
    typer.echo(
        "Built MVP-D2 source quality -> data/processed/mvp_d2/source_quality_scores.jsonl "
        f"(recommendations={source_summary.get('by_recommendation', {})}, diagnostics={len(diagnostics)})"
    )


@app.command("build-calibrated-query-plan")
def build_calibrated_query_plan_command(
    domain: Annotated[str, typer.Option("--domain")] = "ai_investment_tracking",
    max_queries: Annotated[int | None, typer.Option("--max-queries")] = None,
    max_results: Annotated[int | None, typer.Option("--max-results")] = None,
    use_cache: Annotated[bool, typer.Option("--use-cache/--no-cache")] = True,
    skip_pilot: Annotated[bool, typer.Option("--skip-pilot")] = False,
) -> None:
    """Build MVP-D2 pain-oriented calibrated query plan v2."""
    queries = build_calibrated_query_plan(max_queries=max_queries)
    typer.echo(
        "Built MVP-D2 calibrated query plan -> data/processed/mvp_d2/calibrated_query_plan_v2.jsonl "
        f"(queries={len(queries)})"
    )


@app.command("run-calibrated-expansion")
def run_calibrated_expansion_command(
    domain: Annotated[str, typer.Option("--domain")] = "ai_investment_tracking",
    max_queries: Annotated[int | None, typer.Option("--max-queries")] = None,
    max_results: Annotated[int | None, typer.Option("--max-results")] = None,
    use_cache: Annotated[bool, typer.Option("--use-cache/--no-cache")] = True,
    skip_pilot: Annotated[bool, typer.Option("--skip-pilot")] = False,
) -> None:
    """Run MVP-D2 calibrated expansion pilot or report why it is blocked."""
    candidates, pains, summary = run_calibrated_expansion(
        max_queries=max_queries,
        max_results=max_results,
        use_cache=use_cache,
        skip_pilot=skip_pilot,
    )
    typer.echo(
        "Built MVP-D2 calibrated expansion -> outputs/mvp_d2/calibrated_expansion_report.md "
        f"(status={summary.get('status')}, blocked={summary.get('blocked_reason') or 'n/a'}, "
        f"candidates={len(candidates)}, pain_items={len(pains)}, "
        f"should_extract_true={summary.get('should_extract_true', 0)})"
    )


@app.command("compare-expansion-v1-v2")
def compare_expansion_v1_v2_command(
    domain: Annotated[str, typer.Option("--domain")] = "ai_investment_tracking",
    max_queries: Annotated[int | None, typer.Option("--max-queries")] = None,
    max_results: Annotated[int | None, typer.Option("--max-results")] = None,
    use_cache: Annotated[bool, typer.Option("--use-cache/--no-cache")] = True,
    skip_pilot: Annotated[bool, typer.Option("--skip-pilot")] = False,
) -> None:
    """Compare MVP-D v1 expansion yield with MVP-D2 calibrated pilot."""
    comparison = compare_expansion_v1_v2()
    typer.echo(
        "Built MVP-D2 comparison -> outputs/mvp_d2/d2_comparison_report.md "
        f"(result={comparison['result']}, v1_yield={comparison['v1'].get('yield_rate')}, "
        f"v2_yield={comparison['v2'].get('yield_rate')})"
    )


@app.command("build-mvp-d2-report")
def build_mvp_d2_report_command(
    domain: Annotated[str, typer.Option("--domain")] = "ai_investment_tracking",
    max_queries: Annotated[int | None, typer.Option("--max-queries")] = None,
    max_results: Annotated[int | None, typer.Option("--max-results")] = None,
    use_cache: Annotated[bool, typer.Option("--use-cache/--no-cache")] = True,
    skip_pilot: Annotated[bool, typer.Option("--skip-pilot")] = False,
) -> None:
    """Build MVP-D2 summary report from stored outputs."""
    summary = build_mvp_d2_summary_from_stored(domain_id=domain)
    typer.echo(
        "Built MVP-D2 summary -> outputs/mvp_d2/mvp_d2_summary_report.md "
        f"(engineering={summary.engineering_acceptance}, product={summary.product_acceptance}, "
        f"comparison={summary.comparison_result})"
    )


@app.command("run-mvp-d2")
def run_mvp_d2_command(
    domain: Annotated[str, typer.Option("--domain")] = "ai_investment_tracking",
    max_queries: Annotated[int | None, typer.Option("--max-queries")] = None,
    max_results: Annotated[int | None, typer.Option("--max-results")] = None,
    use_cache: Annotated[bool, typer.Option("--use-cache/--no-cache")] = True,
    skip_pilot: Annotated[bool, typer.Option("--skip-pilot")] = False,
) -> None:
    """Run MVP-D2 expansion diagnostics and query calibration end-to-end."""
    summary = run_mvp_d2(
        domain_id=domain,
        max_queries=max_queries,
        max_results=max_results,
        use_cache=use_cache,
        skip_pilot=skip_pilot,
    )
    typer.echo(
        "MVP-D2 complete -> outputs/mvp_d2/mvp_d2_summary_report.md "
        f"(rejected={summary.total_rejected}, queries={summary.generated_v2_queries}, "
        f"pilot_blocked={summary.blocked_reason or 'n/a'}, comparison={summary.comparison_result}, "
        f"engineering={summary.engineering_acceptance}, product={summary.product_acceptance})"
    )





@app.command("detect-search-provider")
def detect_search_provider_command(
    domain: Annotated[str, typer.Option("--domain")] = "ai_investment_tracking",
) -> None:
    from demand_radar.mvp_d3.search_provider_client import detect_provider
    provider, key = detect_provider()
    if provider:
        typer.echo(f"[detect-search-provider] provider={provider} key_len={len(key or '')}")
    else:
        typer.echo("[detect-search-provider] blocked_by_missing_search_provider")


@app.command("run-mvp-d3")
def run_mvp_d3_command(
    domain: Annotated[str, typer.Option("--domain")] = "ai_investment_tracking",
    max_queries: Annotated[int, typer.Option("--max-queries")] = 24,
    max_results_per_query: Annotated[int, typer.Option("--max-results-per-query")] = 5,
    use_cache: Annotated[bool, typer.Option("--use-cache/--no-cache")] = True,
    fake_llm: Annotated[bool, typer.Option("--fake-llm")] = False,
    skip_fetch: Annotated[bool, typer.Option("--skip-fetch")] = False,
) -> None:
    from demand_radar.mvp_d3.mvp_d3_pipeline import run_mvp_d3
    from demand_radar.semantic_merge.llm_client import make_llm_client, FakeLLMClient
    import os
    try:
        from dotenv import load_dotenv; load_dotenv()
    except ImportError:
        pass
    llm_client = None
    if fake_llm:
        llm_client = FakeLLMClient()
    else:
        api_key = os.environ.get("DEMAND_RADAR_LLM_API_KEY", "")
        model = os.environ.get("DEMAND_RADAR_LLM_MODEL", "claude-sonnet-4-6")
        if api_key:
            llm_client = make_llm_client("responses_compatible", {"model": model})
    typer.echo(f"[run-mvp-d3] domain={domain} max_queries={max_queries}")
    result = run_mvp_d3(
        domain_id=domain, max_queries=max_queries,
        max_results_per_query=max_results_per_query,
        use_cache=use_cache, llm_client=llm_client,
        fetch_pages=not skip_fetch,
    )
    typer.echo(f"[run-mvp-d3] provider={result.provider} blocked={result.blocked_reason}")
    typer.echo(f"[run-mvp-d3] gate_allowed={result.gate_allowed} should_extract_true={result.should_extract_true}")
    typer.echo(f"[run-mvp-d3] eng={result.engineering_acceptance} prod={result.product_acceptance}")


@app.command("run-search-pilot")
def run_search_pilot_command(
    max_queries: Annotated[int, typer.Option("--max-queries")] = 24,
    max_results_per_query: Annotated[int, typer.Option("--max-results-per-query")] = 5,
) -> None:
    from demand_radar.mvp_d3.search_pilot_runner import run_search_pilot
    result = run_search_pilot(max_queries=max_queries, max_results_per_query=max_results_per_query)
    typer.echo(f"[run-search-pilot] provider={result.get('provider')} status={result.get('status')}")
    typer.echo(f"[run-search-pilot] gate_allowed={result.get('gate_allowed')} unique_urls={result.get('unique_urls')}")



@app.command("detect-foundation-search-provider")
def detect_foundation_search_provider_command(
    domain: Annotated[str, typer.Option("--domain")] = "ai_investment_tracking",
) -> None:
    from demand_radar.mvp_d4.foundation_search_adapter import detect_provider, check_foundation_version
    ver_ok, ver = check_foundation_version()
    typer.echo(f"[foundation-version] {ver} ok={ver_ok}")
    prov = detect_provider()
    typer.echo(f"[detect-foundation-search-provider] {prov or 'none'}")


@app.command("run-mvp-d4")
def run_mvp_d4_command(
    domain: Annotated[str, typer.Option("--domain")] = "ai_investment_tracking",
    max_queries: Annotated[int, typer.Option("--max-queries")] = 24,
    max_results_per_query: Annotated[int, typer.Option("--max-results-per-query")] = 5,
    use_cache: Annotated[bool, typer.Option("--use-cache/--no-cache")] = True,
    fake_llm: Annotated[bool, typer.Option("--fake-llm")] = False,
) -> None:
    from demand_radar.mvp_d4.foundation_search_pipeline import run_mvp_d4
    from demand_radar.semantic_merge.llm_client import make_llm_client, FakeLLMClient
    import os
    try:
        from dotenv import load_dotenv; load_dotenv()
    except ImportError:
        pass
    llm_client = None
    if fake_llm:
        llm_client = FakeLLMClient()
    else:
        api_key = os.environ.get("DEMAND_RADAR_LLM_API_KEY", "")
        model = os.environ.get("DEMAND_RADAR_LLM_MODEL", "claude-sonnet-4-6")
        if api_key:
            llm_client = make_llm_client("responses_compatible", {"model": model})
    typer.echo(f"[run-mvp-d4] domain={domain} max_queries={max_queries}")
    result = run_mvp_d4(
        domain_id=domain, max_queries=max_queries,
        max_results_per_query=max_results_per_query,
        use_cache=use_cache, llm_client=llm_client,
    )
    typer.echo(f"[run-mvp-d4] provider={result.provider} blocked={result.blocked_reason}")
    typer.echo(f"[run-mvp-d4] gate_allowed={result.gate_allowed} should_extract_true={result.should_extract_true}")
    typer.echo(f"[run-mvp-d4] eng={result.engineering_acceptance} prod={result.product_acceptance}")


@app.command("run-foundation-search-pilot")
def run_foundation_search_pilot_command(
    max_queries: Annotated[int, typer.Option("--max-queries")] = 24,
    max_results_per_query: Annotated[int, typer.Option("--max-results-per-query")] = 5,
) -> None:
    from demand_radar.mvp_d4.foundation_search_pipeline import run_mvp_d4
    result = run_mvp_d4(max_queries=max_queries, max_results_per_query=max_results_per_query)
    typer.echo(f"[foundation-search-pilot] provider={result.provider} gate_allowed={result.gate_allowed}")



@app.command("detect-foundation-search-provider")
def detect_foundation_search_provider_command(
    domain: Annotated[str, typer.Option("--domain")] = "ai_investment_tracking",
) -> None:
    from demand_radar.mvp_d4.foundation_search_adapter import detect_provider, check_foundation_version
    ver_ok, ver = check_foundation_version()
    typer.echo(f"[foundation-version] {ver} ok={ver_ok}")
    prov = detect_provider()
    typer.echo(f"[detect-foundation-search-provider] {prov or 'none'}")


@app.command("run-mvp-d4")
def run_mvp_d4_command(
    domain: Annotated[str, typer.Option("--domain")] = "ai_investment_tracking",
    max_queries: Annotated[int, typer.Option("--max-queries")] = 24,
    max_results_per_query: Annotated[int, typer.Option("--max-results-per-query")] = 5,
    use_cache: Annotated[bool, typer.Option("--use-cache/--no-cache")] = True,
    fake_llm: Annotated[bool, typer.Option("--fake-llm")] = False,
) -> None:
    from demand_radar.mvp_d4.foundation_search_pipeline import run_mvp_d4
    from demand_radar.semantic_merge.llm_client import make_llm_client, FakeLLMClient
    import os
    try:
        from dotenv import load_dotenv; load_dotenv()
    except ImportError:
        pass
    llm_client = None
    if fake_llm:
        llm_client = FakeLLMClient()
    else:
        api_key = os.environ.get("DEMAND_RADAR_LLM_API_KEY", "")
        model = os.environ.get("DEMAND_RADAR_LLM_MODEL", "claude-sonnet-4-6")
        if api_key:
            llm_client = make_llm_client("responses_compatible", {"model": model})
    typer.echo(f"[run-mvp-d4] domain={domain} max_queries={max_queries}")
    result = run_mvp_d4(
        domain_id=domain, max_queries=max_queries,
        max_results_per_query=max_results_per_query,
        use_cache=use_cache, llm_client=llm_client,
    )
    typer.echo(f"[run-mvp-d4] provider={result.provider} blocked={result.blocked_reason}")
    typer.echo(f"[run-mvp-d4] gate_allowed={result.gate_allowed} should_extract_true={result.should_extract_true}")
    typer.echo(f"[run-mvp-d4] eng={result.engineering_acceptance} prod={result.product_acceptance}")


@app.command("llm-semantic-merge-judge")
def llm_semantic_merge_judge_command(
    fake_llm: Annotated[bool, typer.Option("--fake-llm", help="Use FakeLLMClient instead of real API.")] = False,
) -> None:
    """Run Stage 2.9 LLM semantic merge judge (writes to llm_* paths)."""
    from demand_radar.semantic_merge.llm_client import FakeLLMClient

    client = FakeLLMClient() if fake_llm else None
    judgments = run_llm_semantic_merge_judge(client=client)
    auto_confirmed = sum(1 for j in judgments if j.auto_action == "auto_confirm")
    auto_rejected = sum(1 for j in judgments if j.auto_action == "auto_reject")
    human_exceptions = sum(1 for j in judgments if j.auto_action == "human_exception")
    typer.echo(
        "Built LLM semantic merge judgments -> data/processed/llm_semantic_merge_judgments.jsonl "
        f"(judgments={len(judgments)}, auto_confirmed={auto_confirmed}, "
        f"auto_rejected={auto_rejected}, human_exceptions={human_exceptions})"
    )


@app.command("build-llm-ai-reviewed-groups")
def build_llm_ai_reviewed_groups_command() -> None:
    """Build AI reviewed cluster groups from LLM judgments (writes to llm_* paths)."""
    groups = build_llm_ai_reviewed_cluster_groups()
    summary = build_llm_ai_reviewed_groups_report()
    typer.echo(
        "Built LLM AI reviewed cluster groups -> data/processed/llm_ai_reviewed_cluster_groups.jsonl "
        f"(groups={len(groups)}, clusters={summary.included_clusters})"
    )


@app.command("build-llm-semantic-merge-report")
def build_llm_semantic_merge_report_command() -> None:
    """Build the LLM semantic merge judgment report."""
    summary = build_llm_semantic_merge_report()
    typer.echo(
        "Built LLM semantic merge report -> outputs/llm_semantic_merge_judgment_report.md "
        f"(human_exception_rate={summary.human_exception_rate})"
    )


@app.command("build-llm-human-exception-report")
def build_llm_human_exception_report_command() -> None:
    """Build the LLM human exception queue report."""
    summary = build_llm_human_exception_report()
    typer.echo(
        "Built LLM human exception report -> outputs/llm_human_exception_queue_report.md "
        f"(exceptions={summary.exceptions})"
    )


@app.command("compare-semantic-merge")
def compare_semantic_merge_command() -> None:
    """Build the rule_based vs LLM semantic merge comparison report."""
    summary = build_semantic_merge_comparison_report()
    typer.echo(
        "Built comparison report -> outputs/llm_semantic_merge_comparison_report.md "
        f"(rule_exc_rate={summary.rule_based_exception_rate}, "
        f"llm_exc_rate={summary.llm_exception_rate}, "
        f"maybe_to_confirm={summary.maybe_to_confirm})"
    )


@app.command("run-stage29")
def run_stage29(
    input: Annotated[
        Path | None,
        typer.Option("--input", exists=True, readable=True, help="Optional CSV or JSONL input file."),
    ] = None,
    fake_llm: Annotated[bool, typer.Option("--fake-llm", help="Use FakeLLMClient (no API calls).")] = False,
) -> None:
    """Run Stage 2.9: real LLM semantic merge pilot with comparison report."""
    from demand_radar.semantic_merge.llm_client import FakeLLMClient

    init(reset=False)
    if input is not None:
        _run_stage2_core(input)
        candidates = suggest_cluster_merges()
        typer.echo(
            "Generated merge candidates -> data/processed/cluster_merge_candidates.jsonl "
            f"(candidates={len(candidates)})"
        )
        merge_summary = build_merge_report()
        typer.echo(
            "Built merge suggestions report -> outputs/cluster_merge_suggestions.md "
            f"(candidates={merge_summary.merge_candidates})"
        )
        # Run rule_based semantic merge (Stage 2.8) for baseline
        rb_judgments = run_semantic_merge_judge()
        rb_confirmed = sum(1 for j in rb_judgments if j.auto_action == "auto_confirm")
        rb_rejected = sum(1 for j in rb_judgments if j.auto_action == "auto_reject")
        rb_exceptions = sum(1 for j in rb_judgments if j.auto_action == "human_exception")
        typer.echo(
            "Built rule_based judgments -> data/processed/semantic_merge_judgments.jsonl "
            f"(judgments={len(rb_judgments)}, auto_confirmed={rb_confirmed}, "
            f"auto_rejected={rb_rejected}, human_exceptions={rb_exceptions})"
        )
        build_semantic_merge_report()
        build_human_exception_report()
        rule_groups = build_ai_reviewed_cluster_groups()
        build_ai_reviewed_groups_report()
        typer.echo(f"Rule-based AI groups: {len(rule_groups)}")

    # LLM semantic merge pilot
    llm_client = FakeLLMClient() if fake_llm else None
    llm_judgments = run_llm_semantic_merge_judge(client=llm_client)
    llm_confirmed = sum(1 for j in llm_judgments if j.auto_action == "auto_confirm")
    llm_rejected = sum(1 for j in llm_judgments if j.auto_action == "auto_reject")
    llm_exceptions = sum(1 for j in llm_judgments if j.auto_action == "human_exception")
    typer.echo(
        "Built LLM judgments -> data/processed/llm_semantic_merge_judgments.jsonl "
        f"(judgments={len(llm_judgments)}, auto_confirmed={llm_confirmed}, "
        f"auto_rejected={llm_rejected}, human_exceptions={llm_exceptions})"
    )
    llm_groups = build_llm_ai_reviewed_cluster_groups()
    llm_group_summary = build_llm_ai_reviewed_groups_report()
    typer.echo(
        f"Built LLM AI groups -> data/processed/llm_ai_reviewed_cluster_groups.jsonl "
        f"(groups={len(llm_groups)}, clusters={llm_group_summary.included_clusters})"
    )
    build_llm_semantic_merge_report()
    build_llm_human_exception_report()

    comparison = build_semantic_merge_comparison_report()
    typer.echo(
        "Built comparison report -> outputs/llm_semantic_merge_comparison_report.md "
        f"(rule_exc_rate={comparison.rule_based_exception_rate}, "
        f"llm_exc_rate={comparison.llm_exception_rate}, "
        f"maybe_to_confirm={comparison.maybe_to_confirm}, "
        f"llm_groups={comparison.llm_ai_groups})"
    )
    batch_summary = build_batch_summary_report()
    typer.echo(
        "Built batch summary -> outputs/batch_summary_report.md "
        f"(ready_for_truth_scoring={batch_summary.readiness.ready_for_truth_scoring})"
    )
    llm_label = "FakeLLM" if fake_llm else "LLM"
    typer.echo(
        f"Stage 2.9 complete — {llm_label} 已处理 {llm_confirmed} 条自动确认、"
        f"{llm_rejected} 条自动拒绝，{llm_exceptions} 条进入人工异常队列。"
    )



@app.command("calibrate-llm-semantic-merge")
def calibrate_llm_semantic_merge_command(
    fake_llm: Annotated[bool, typer.Option("--fake-llm", help="Use FakeLLMClient instead of real API.")] = False,
    no_cache: Annotated[bool, typer.Option("--no-cache", help="Skip reading cache; write new results.")] = False,
    force_rerun: Annotated[bool, typer.Option("--force-rerun", help="Ignore and overwrite existing cache entries.")] = False,
    clear_cache: Annotated[bool, typer.Option("--clear-cache", help="Clear LLM semantic merge cache before running.")] = False,
) -> None:
    """Run Stage 2.9C/D calibrated LLM semantic merge judge."""
    from demand_radar.semantic_merge.calibration_runner import run_calibrated_llm_judge
    from demand_radar.semantic_merge.llm_client import FakeLLMClient as _FakeLLM

    llm_client = _FakeLLM() if fake_llm else None
    judgments, preflight_results, cache_stats = run_calibrated_llm_judge(
        client=llm_client,
        no_cache=no_cache,
        force_rerun=force_rerun,
        clear_cache_before=clear_cache,
    )
    auto_confirmed = sum(1 for j in judgments if j.auto_action == "auto_confirm")
    auto_rejected = sum(1 for j in judgments if j.auto_action == "auto_reject")
    human_exceptions = sum(1 for j in judgments if j.auto_action == "human_exception")
    pf_ok = sum(1 for r in preflight_results if r.status == "ok")
    pf_repaired = sum(1 for r in preflight_results if r.status == "repaired")
    pf_invalid = sum(1 for r in preflight_results if r.status == "invalid")
    typer.echo(
        "Calibrated LLM judgments -> data/processed/calibrated_llm_semantic_merge_judgments.jsonl "
        f"(judgments={len(judgments)}, auto_confirmed={auto_confirmed}, "
        f"auto_rejected={auto_rejected}, human_exceptions={human_exceptions}, "
        f"preflight ok={pf_ok} repaired={pf_repaired} invalid={pf_invalid})"
    )
    typer.echo(
        f"Cache: reads={cache_stats.reads} writes={cache_stats.writes} "
        f"bypassed={cache_stats.bypassed} stale_prevented={cache_stats.stale_prevented}"
    )


@app.command("build-calibrated-ai-reviewed-groups")
def build_calibrated_ai_reviewed_groups_command() -> None:
    """Build calibrated AI reviewed cluster groups."""
    from demand_radar.semantic_merge.calibration_runner import build_calibrated_ai_reviewed_groups
    groups = build_calibrated_ai_reviewed_groups()
    typer.echo(
        "Built calibrated AI groups -> data/processed/calibrated_llm_ai_reviewed_cluster_groups.jsonl "
        f"(groups={len(groups)})"
    )


@app.command("build-llm-calibration-report")
def build_llm_calibration_report_command() -> None:
    """Build the Stage 2.9C calibration report."""
    from demand_radar.semantic_merge.calibration_report import build_llm_calibration_report
    summary = build_llm_calibration_report()
    typer.echo(
        "Built calibration report -> outputs/llm_semantic_merge_calibration_report.md "
        f"(cal_exception_rate={summary.cal_exception_rate}, "
        f"cal_groups={summary.cal_ai_groups}, "
        f"rejects_unlocked={summary.rejects_unlocked})"
    )


@app.command("run-stage29c")
def run_stage29c(
    input: Annotated[
        Path | None,
        typer.Option("--input", exists=True, readable=True, help="Optional CSV or JSONL input file."),
    ] = None,
    fake_llm: Annotated[bool, typer.Option("--fake-llm", help="Use FakeLLMClient (no API calls).")] = False,
    no_cache: Annotated[bool, typer.Option("--no-cache", help="Skip reading cache; write new results.")] = False,
    force_rerun: Annotated[bool, typer.Option("--force-rerun", help="Ignore and overwrite existing cache entries.")] = False,
    clear_cache: Annotated[bool, typer.Option("--clear-cache", help="Clear LLM semantic merge cache before running.")] = False,
) -> None:
    """Run Stage 2.9C/D: calibrated LLM with preflight, versioned cache, split gate."""
    from demand_radar.semantic_merge.calibration_runner import (
        build_calibrated_ai_reviewed_groups,
        run_calibrated_llm_judge,
    )
    from demand_radar.semantic_merge.calibration_report import build_llm_calibration_report
    from demand_radar.semantic_merge.llm_client import FakeLLMClient as _FakeLLM
    from demand_radar.config.load_config import load_yaml as _load_yaml

    init(reset=False)
    if input is not None:
        _run_stage2_core(input)
        candidates = suggest_cluster_merges()
        typer.echo(
            "Generated merge candidates -> data/processed/cluster_merge_candidates.jsonl "
            f"(candidates={len(candidates)})"
        )
        build_merge_report()

    llm_client = _FakeLLM() if fake_llm else None
    judgments, preflight_results, cache_stats = run_calibrated_llm_judge(
        client=llm_client,
        no_cache=no_cache,
        force_rerun=force_rerun,
        clear_cache_before=clear_cache,
    )
    auto_confirmed = sum(1 for j in judgments if j.auto_action == "auto_confirm")
    auto_rejected = sum(1 for j in judgments if j.auto_action == "auto_reject")
    human_exceptions = sum(1 for j in judgments if j.auto_action == "human_exception")
    pf_ok = sum(1 for r in preflight_results if r.status == "ok")
    pf_repaired = sum(1 for r in preflight_results if r.status == "repaired")
    pf_invalid = sum(1 for r in preflight_results if r.status == "invalid")
    typer.echo(
        "Calibrated LLM judgments -> data/processed/calibrated_llm_semantic_merge_judgments.jsonl "
        f"(judgments={len(judgments)}, auto_confirmed={auto_confirmed}, "
        f"auto_rejected={auto_rejected}, human_exceptions={human_exceptions})"
    )
    typer.echo(f"Preflight: ok={pf_ok} repaired={pf_repaired} invalid={pf_invalid}")
    typer.echo(
        f"Cache: reads={cache_stats.reads} writes={cache_stats.writes} "
        f"bypassed={cache_stats.bypassed} stale_prevented={cache_stats.stale_prevented}"
    )

    cal_groups = build_calibrated_ai_reviewed_groups()
    typer.echo(
        "Built calibrated AI groups -> data/processed/calibrated_llm_ai_reviewed_cluster_groups.jsonl "
        f"(groups={len(cal_groups)})"
    )

    # Build run metadata for calibration report
    _cfg = _load_yaml("configs/semantic_merge_config.yaml")
    _scfg = _cfg.get("semantic_merge", {})
    _cal = _scfg.get("calibration", {})
    _llm = _scfg.get("llm", {})
    run_meta = {
        "prompt_version": _cal.get("prompt_version", "unknown"),
        "gate_policy_version": _cal.get("gate_policy_version", "unknown"),
        "provider": _llm.get("provider", "fake" if fake_llm else "unknown"),
        "cache_enabled": _scfg.get("batch", {}).get("cache_enabled", True),
        "force_rerun": force_rerun,
        "no_cache": no_cache,
        "clear_cache_used": clear_cache,
    }

    calibration_summary = build_llm_calibration_report(cache_stats=cache_stats, run_meta=run_meta)
    typer.echo(
        "Built calibration report -> outputs/llm_semantic_merge_calibration_report.md "
        f"(cal_exception_rate={calibration_summary.cal_exception_rate}, "
        f"cal_groups={calibration_summary.cal_ai_groups})"
    )

    batch_summary = build_batch_summary_report()
    typer.echo(
        "Built batch summary -> outputs/batch_summary_report.md "
        f"(ready_for_truth_scoring={batch_summary.readiness.ready_for_truth_scoring})"
    )
    label = "FakeLLM" if fake_llm else "CalibLLM"
    typer.echo(
        f"Stage 2.9C complete ({label}): confirmed={auto_confirmed} rejected={auto_rejected} "
        f"exceptions={human_exceptions} groups={len(cal_groups)}"
    )


@app.command("clear-llm-semantic-merge-cache")
def clear_llm_semantic_merge_cache_command(
    cache_path: Annotated[str, typer.Option("--cache-path", help="Path to cache file.")] = "data/cache/llm_semantic_merge_cache.jsonl",
) -> None:
    """Clear the LLM semantic merge cache (Stage 2.9D)."""
    from demand_radar.semantic_merge.llm_cache import LLMSemanticMergeCache
    cache = LLMSemanticMergeCache(path=cache_path)
    count = cache.clear()
    typer.echo(f"Cleared {count} entries from LLM semantic merge cache: {cache_path}")


@app.command("review-ui")
def review_ui(
    port: Annotated[int, typer.Option("--port", help="Local Streamlit port.")] = 8501,
) -> None:
    """Launch the local Streamlit calibration review UI."""

    app_path = Path(__file__).parent / "ui" / "review_app.py"
    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.port",
        str(port),
        "--server.address",
        "127.0.0.1",
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
    ]
    typer.echo(f"姝ｅ湪鍚姩瀹℃牳鐣岄潰锛歨ttp://127.0.0.1:{port}")
    raise typer.Exit(subprocess.call(command))


@calibration_review_app.command("add")
def add_calibration_review(
    raw_signal_id: Annotated[str, typer.Option("--raw-signal-id", help="Raw signal ID under review.")],
    label: Annotated[str, typer.Option("--label", help="Calibration label.")],
    note: Annotated[str, typer.Option("--note", help="Human reviewer note.")],
    normalized_signal_id: Annotated[str | None, typer.Option("--normalized-signal-id")] = None,
    pain_point_id: Annotated[str | None, typer.Option("--pain-point-id")] = None,
    expected_persona: Annotated[str | None, typer.Option("--expected-persona")] = None,
    expected_evidence_quote: Annotated[str | None, typer.Option("--expected-evidence-quote")] = None,
    expected_pain_description: Annotated[str | None, typer.Option("--expected-pain-description")] = None,
    should_be_quarantined: Annotated[bool | None, typer.Option("--should-be-quarantined")] = None,
) -> None:
    """Append a human calibration review record."""

    review = append_calibration_review(
        raw_signal_id=raw_signal_id,
        normalized_signal_id=normalized_signal_id,
        pain_point_id=pain_point_id,
        label=label,
        reviewer_note=note,
        expected_persona=expected_persona,
        expected_evidence_quote=expected_evidence_quote,
        expected_pain_description=expected_pain_description,
        should_be_quarantined=should_be_quarantined,
    )
    typer.echo(f"Added calibration review {review.review_id} -> data/processed/calibration_reviews.jsonl")


def _clear_regenerated_stage2_files() -> None:
    for path in STAGE2_REGENERATED_FILES:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")


def _run_stage2_core(input: Path) -> None:
    _clear_regenerated_stage2_files()
    imported = import_file(input)
    typer.echo(f"Imported {len(imported)} raw signals -> data/raw/raw_signals.jsonl")
    normalized = normalize_signals()
    typer.echo(f"Normalized {len(normalized)} signals -> data/processed/normalized_signals.jsonl")
    pain_points = run_pain_extraction()
    typer.echo(f"Extracted {len(pain_points)} valid pain points -> data/processed/pain_points.jsonl")
    pain_summary = build_pain_points_report()
    typer.echo(
        "Built pain report -> outputs/pain_points_report.md "
        f"(raw={pain_summary.raw_signals}, normalized={pain_summary.normalized_signals}, "
        f"pain_points={pain_summary.pain_points}, quarantine={pain_summary.quarantined_items})"
    )
    calibration_summary = build_calibration_report()
    typer.echo(
        "Built calibration report -> outputs/calibration_report.md "
        f"(reviews={calibration_summary.calibration_reviews})"
    )
    clusters = run_demand_clustering()
    typer.echo(f"Generated {len(clusters)} demand clusters -> data/processed/demand_clusters.jsonl")
    cluster_summary = build_cluster_report()
    typer.echo(
        "Built cluster report -> outputs/demand_clusters_report.md "
        f"(pain_points={cluster_summary.pain_points}, clusters={cluster_summary.demand_clusters}, "
        f"singleton={cluster_summary.singleton_clusters}, invalid={cluster_summary.invalid_clusters}, "
        f"cluster_reviews={cluster_summary.cluster_reviews})"
    )



@app.command("run-truth-scoring")
def run_truth_scoring_command(
    source: Annotated[str, typer.Option("--source")] = "calibrated_llm",
) -> None:
    """Score reviewed cluster groups using Stage 3 Truth Scoring."""
    scores = run_truth_scoring(source=source)
    level_counts = {}
    for s in scores:
        level_counts[s.truth_level] = level_counts.get(s.truth_level, 0) + 1
    proceed = sum(1 for s in scores if s.recommended_next_action == "proceed_to_fit_scoring")
    typer.echo(
        f"Truth scoring complete: {len(scores)} scores "
        f"(strong={level_counts.get('strong', 0)}, medium={level_counts.get('medium', 0)}, "
        f"weak={level_counts.get('weak', 0)}, insufficient={level_counts.get('insufficient', 0)}, "
        f"proceed_to_fit_scoring={proceed})"
    )
    typer.echo("Written -> data/processed/truth_scores.jsonl")


@app.command("build-truth-report")
def build_truth_report_command() -> None:
    """Build truth_scoring_report.md from persisted truth scores."""
    scores = load_truth_scores()
    if not scores:
        typer.echo("No truth scores found. Run run-truth-scoring first.")
        raise typer.Exit(1)
    build_truth_scoring_report(scores)
    typer.echo(f"Built truth report -> outputs/truth_scoring_report.md ({len(scores)} scores)")


@app.command("build-top-truth-candidates-report")
def build_top_truth_candidates_report_command() -> None:
    """Build top_truth_candidates_report.md (strong/medium only)."""
    scores = load_truth_scores()
    if not scores:
        typer.echo("No truth scores found. Run run-truth-scoring first.")
        raise typer.Exit(1)
    build_top_truth_candidates_report(scores)
    top = [s for s in scores if s.truth_level in ("strong", "medium")]
    typer.echo(f"Built top candidates report -> outputs/top_truth_candidates_report.md ({len(top)} candidates)")


@app.command("run-stage3")
def run_stage3(
    source: Annotated[str, typer.Option("--source")] = "calibrated_llm",
) -> None:
    """Stage 3: Truth Scoring Loop v1."""
    typer.echo(f"Stage 3 Truth Scoring starting (source={source})")
    scores = run_truth_scoring(source=source)
    level_counts = {}
    for s in scores:
        level_counts[s.truth_level] = level_counts.get(s.truth_level, 0) + 1
    proceed = sum(1 for s in scores if s.recommended_next_action == "proceed_to_fit_scoring")
    typer.echo(
        f"Scored {len(scores)} groups: strong={level_counts.get('strong', 0)}, "
        f"medium={level_counts.get('medium', 0)}, weak={level_counts.get('weak', 0)}, "
        f"insufficient={level_counts.get('insufficient', 0)}"
    )
    typer.echo(f"proceed_to_fit_scoring={proceed}")
    typer.echo("Written -> data/processed/truth_scores.jsonl")

    build_truth_scoring_report(scores)
    typer.echo("Built -> outputs/truth_scoring_report.md")

    build_top_truth_candidates_report(scores)
    typer.echo("Built -> outputs/top_truth_candidates_report.md")

    build_batch_summary_report()
    typer.echo("Updated -> outputs/batch_summary_report.md")

    typer.echo("Stage 3 complete.")



@app.command("analyze-evidence-gaps")
def analyze_evidence_gaps_command() -> None:
    """Analyze evidence gaps for medium/strong truth candidates."""
    scores = load_truth_scores()
    if not scores:
        typer.echo("No truth scores found. Run run-stage3 first.")
        raise typer.Exit(1)
    score_dicts = [s.model_dump() for s in scores]
    gaps = analyze_gaps(score_dicts)
    write_gap_analysis(gaps)
    plans = build_collection_plans(gaps)
    write_collection_plans(plans)
    by_pri = {}
    for g in gaps:
        by_pri[g.priority] = by_pri.get(g.priority, 0) + 1
    total_signals = sum(p.target_new_signals for p in plans)
    typer.echo(
        f"Evidence gap analysis complete: {len(gaps)} candidates analyzed "
        f"(high={by_pri.get('high',0)}, medium={by_pri.get('medium',0)}, "
        f"low={by_pri.get('low',0)}, target_new_signals={total_signals})"
    )
    typer.echo("Written -> data/processed/evidence_gap_analysis.jsonl")
    typer.echo("Written -> data/processed/targeted_signal_collection_plan.jsonl")


@app.command("build-evidence-gap-report")
def build_evidence_gap_report_command() -> None:
    """Build evidence_gap_report.md from persisted gap analysis."""
    gaps = load_gap_analysis()
    if not gaps:
        typer.echo("No gap analysis found. Run analyze-evidence-gaps first.")
        raise typer.Exit(1)
    build_evidence_gap_report(gaps)
    typer.echo(f"Built -> outputs/evidence_gap_report.md ({len(gaps)} gaps)")


@app.command("build-targeted-signal-plan")
def build_targeted_signal_plan_command() -> None:
    """Build targeted_signal_collection_plan.md from persisted plans."""
    from demand_radar.evidence_gap.evidence_gap_store import load_collection_plans
    plans = load_collection_plans()
    if not plans:
        typer.echo("No collection plans found. Run analyze-evidence-gaps first.")
        raise typer.Exit(1)
    build_targeted_signal_plan_report(plans)
    typer.echo(f"Built -> outputs/targeted_signal_collection_plan.md ({len(plans)} plans)")


@app.command("run-stage32")
def run_stage32(
    source: Annotated[str, typer.Option("--source")] = "calibrated_llm",
) -> None:
    """Stage 3.2: Evidence Gap Analysis & Targeted Signal Expansion."""
    typer.echo("Stage 3.2 Evidence Gap Analysis starting")

    # Ensure truth scores exist
    scores = load_truth_scores()
    if not scores:
        typer.echo("No truth scores found, running Stage 3 first...")
        scores_raw = run_truth_scoring(source=source)
        build_truth_scoring_report(scores_raw)
        build_top_truth_candidates_report(scores_raw)
        scores = scores_raw

    typer.echo(f"Loaded {len(scores)} truth scores")
    score_dicts = [s.model_dump() for s in scores]
    gaps = analyze_gaps(score_dicts)
    write_gap_analysis(gaps)
    plans = build_collection_plans(gaps)
    write_collection_plans(plans)

    by_pri = {}
    for g in gaps:
        by_pri[g.priority] = by_pri.get(g.priority, 0) + 1
    total_signals = sum(p.target_new_signals for p in plans)

    typer.echo(
        f"Evidence gaps: {len(gaps)} "
        f"(high={by_pri.get('high',0)}, medium={by_pri.get('medium',0)}, "
        f"low={by_pri.get('low',0)})"
    )
    typer.echo(f"Target new signals: {total_signals}")
    typer.echo("Written -> data/processed/evidence_gap_analysis.jsonl")
    typer.echo("Written -> data/processed/targeted_signal_collection_plan.jsonl")

    build_evidence_gap_report(gaps)
    typer.echo("Built -> outputs/evidence_gap_report.md")

    build_targeted_signal_plan_report(plans)
    typer.echo("Built -> outputs/targeted_signal_collection_plan.md")

    build_batch_summary_report()
    typer.echo("Updated -> outputs/batch_summary_report.md")

    typer.echo("Stage 3.2 complete.")



@app.command("build-targeted-signal-template")
def build_targeted_signal_template_command() -> None:
    """Build targeted signal collection template CSV for Stage 3.3."""
    rows = build_template()
    typer.echo(f"Template built: {len(rows)} rows -> examples/stage33_targeted_signal_template.csv")


@app.command("validate-targeted-signals")
def validate_targeted_signals_command(
    input: Annotated[Path, typer.Option("--input")] = Path("examples/real_signal_samples_stage33.csv"),
) -> None:
    """Validate targeted signals from filled CSV."""
    validations = validate_targeted_signals(input)
    from collections import Counter
    by_status = Counter(v.status for v in validations)
    typer.echo(
        f"Validation complete: {len(validations)} signals "
        f"(valid={by_status.get('valid',0)}, warning={by_status.get('warning',0)}, "
        f"invalid={by_status.get('invalid',0)}, excluded={by_status.get('excluded',0)})"
    )
    typer.echo("Written -> data/processed/targeted_signal_validation.jsonl")


@app.command("build-combined-stage33-input")
def build_combined_stage33_input_command(
    base: Annotated[Path, typer.Option("--base")] = Path("examples/real_signal_samples_stage26.csv"),
    targeted: Annotated[Path, typer.Option("--targeted")] = Path("examples/real_signal_samples_stage33.csv"),
) -> None:
    """Build combined input CSV (base + valid targeted signals)."""
    result = build_combined_input(base_path=base, targeted_path=targeted)
    typer.echo(
        f"Combined input built: base={result['base_rows']}, "
        f"targeted={result['targeted_rows_included']}, "
        f"total={result['combined_rows']}, duplicates_removed={result['duplicates_removed']}"
    )
    typer.echo("Written -> examples/combined_signal_samples_stage33.csv")


@app.command("build-targeted-expansion-report")
def build_targeted_expansion_report_command() -> None:
    """Build targeted_expansion_report.md."""
    summary = load_expansion_summary()
    validations = load_validations()
    build_targeted_expansion_report(summary, validations)
    typer.echo("Built -> outputs/targeted_expansion_report.md")


@app.command("build-truth-score-delta-report")
def build_truth_score_delta_report_command() -> None:
    """Build truth_score_delta_report.md."""
    deltas = load_truth_score_deltas()
    build_truth_score_delta_report(deltas)
    typer.echo("Built -> outputs/truth_score_delta_report.md")


@app.command("run-stage33")
def run_stage33(
    targeted: Annotated[Path, typer.Option("--targeted")] = Path("examples/real_signal_samples_stage33.csv"),
) -> None:
    """Stage 3.3: Build template, validate, combine, and report (no LLM)."""
    typer.echo("Stage 3.3 starting (template + validate + combine + report)")
    targeted_path = targeted if targeted.exists() else None
    if targeted_path is None:
        typer.echo(f"Note: {targeted} not found, running template-only mode")
    summary = _run_stage33_pipeline(targeted_path=targeted_path)
    typer.echo(
        f"Stage 3.3 complete: template={summary.template_rows}, "
        f"combined={summary.combined_input_rows}"
    )
    build_batch_summary_report()
    typer.echo("Updated -> outputs/batch_summary_report.md")


@app.command("run-stage33-full")
def run_stage33_full(
    targeted: Annotated[Path, typer.Option("--targeted")] = Path("examples/real_signal_samples_stage33.csv"),
    skip_llm: Annotated[bool, typer.Option("--skip-llm")] = False,
) -> None:
    """Stage 3.3 full run: template + validate + combine + LLM rerun + delta report.
    WARNING: triggers LLM calls (requires API key unless --skip-llm).
    """
    import os as _os
    typer.echo("Stage 3.3-full starting")
    if not skip_llm:
        if not _os.environ.get("DEMAND_RADAR_LLM_API_KEY"):
            typer.echo("ERROR: DEMAND_RADAR_LLM_API_KEY not set. Use --skip-llm to skip LLM rerun.")
            raise typer.Exit(1)

    # Step 1: template + validate + combine
    targeted_path = targeted if targeted.exists() else None
    summary = _run_stage33_pipeline(targeted_path=targeted_path)
    typer.echo(
        f"Step 1 done: template={summary.template_rows}, "
        f"valid={summary.valid_signals}, combined={summary.combined_input_rows}"
    )

    # Step 2: save before-truth scores for delta comparison
    from demand_radar.truth_scoring.truth_store import load_truth_scores
    from demand_radar.targeted_expansion.targeted_schema import TruthScoreDelta
    from demand_radar.targeted_expansion.expansion_store import write_truth_score_deltas
    before_scores = {s.source_group_id: s for s in load_truth_scores()}

    combined_input = Path("examples/combined_signal_samples_stage33.csv")

    if not skip_llm and combined_input.exists():
        import subprocess as _sp
        import sys as _sys
        # Step 3: run stage 2.6 on combined input
        typer.echo("Step 2: Running Stage 2.6 on combined input...")
        result_26 = _sp.run(
            [_sys.executable, "-m", "demand_radar.cli", "run-stage26", "--input", str(combined_input)],
            capture_output=True, text=True
        )
        if result_26.returncode != 0:
            typer.echo(f"WARNING: Stage 2.6 exited with code {result_26.returncode}")
            if result_26.stderr:
                typer.echo(result_26.stderr[:500])
        else:
            typer.echo("Stage 2.6 done.")

        # Step 4: run stage 2.9C on combined input with force-rerun
        typer.echo("Step 3: Running Stage 2.9C semantic merge on combined input (force-rerun)...")
        result_29c = _sp.run(
            [_sys.executable, "-m", "demand_radar.cli", "run-stage29c",
             "--input", str(combined_input), "--force-rerun"],
            capture_output=True, text=True
        )
        if result_29c.returncode != 0:
            typer.echo(f"WARNING: Stage 2.9C exited with code {result_29c.returncode}")
            if result_29c.stderr:
                typer.echo(result_29c.stderr[:500])
        else:
            typer.echo("Stage 2.9C done.")
            # Print key output lines
            for line in result_29c.stdout.splitlines():
                if any(k in line for k in ["auto_confirm", "auto_reject", "exception", "failure", "groups"]):
                    typer.echo("  " + line)
    else:
        if skip_llm:
            typer.echo("Step 2-3: Skipped (--skip-llm)")
        else:
            typer.echo(f"Step 2-3: Skipped (combined input not found at {combined_input})")

    # Step 5: run truth scoring
    typer.echo("Step 4: Running Stage 3 truth scoring...")
    scores = run_truth_scoring(source="calibrated_llm")
    typer.echo(f"Truth scoring done: {len(scores)} scores")

    # Step 6: compute delta
    after_scores = {s.source_group_id: s for s in scores}
    all_group_ids = set(list(before_scores.keys()) + list(after_scores.keys()))
    from demand_radar.state.raw_store import utc_now_iso
    deltas = []
    for gid in all_group_ids:
        before = before_scores.get(gid)
        after = after_scores.get(gid)
        b_score = before.truth_score if before else None
        a_score = after.truth_score if after else None
        delta_val = round(a_score - b_score, 2) if (a_score is not None and b_score is not None) else None
        improved = []
        if before and after:
            for dim in ["pain_evidence_strength", "frequency_repetition", "existing_workaround",
                        "willingness_to_pay", "persona_clarity"]:
                b_dim = before.dimension_scores.get(dim, 0)
                a_dim = after.dimension_scores.get(dim, 0)
                if a_dim > b_dim + 0.5:
                    improved.append(dim)
        deltas.append(TruthScoreDelta(
            source_group_id=gid,
            group_title_zh=after.group_title_zh if after else (before.group_title_zh if before else gid),
            before_truth_score=b_score,
            after_truth_score=a_score,
            delta=delta_val,
            before_truth_level=before.truth_level if before else None,
            after_truth_level=after.truth_level if after else None,
            before_next_action=before.recommended_next_action if before else None,
            after_next_action=after.recommended_next_action if after else None,
            improved_dimensions=improved,
            remaining_gaps=[],
            created_at=utc_now_iso(),
        ))
    write_truth_score_deltas(deltas)
    typer.echo(f"Delta report: {len(deltas)} candidates compared")

    improved_count = sum(1 for d in deltas if d.delta and d.delta > 0)
    new_strong = sum(1 for d in deltas if d.after_truth_level == "strong" and (d.before_truth_level != "strong"))
    new_proceed = sum(1 for d in deltas if d.after_next_action == "proceed_to_fit_scoring"
                      and d.before_next_action != "proceed_to_fit_scoring")

    build_truth_score_delta_report(deltas)
    typer.echo("Built -> outputs/truth_score_delta_report.md")
    build_batch_summary_report()
    typer.echo(
        f"Stage 3.3-full complete: improved={improved_count}, "
        f"new_strong={new_strong}, new_proceed_to_fit={new_proceed}"
    )


from demand_radar.lineage.lineage_propagator import (
    snapshot_truth_state,
    load_snapshot_truth_scores,
    load_current_truth_scores,
)
from demand_radar.lineage.evidence_attributor import attribute_targeted_evidence
from demand_radar.lineage.candidate_matcher import match_candidate_lineage
from demand_radar.lineage.stable_delta import compute_stable_deltas
from demand_radar.lineage.lineage_report import (
    build_candidate_lineage_report,
    build_targeted_evidence_attribution_report,
    build_stable_truth_score_delta_report,
)
from demand_radar.lineage.lineage_store import (
    write_candidate_lineage,
    write_targeted_evidence_attribution,
    write_stable_truth_score_delta,
    load_candidate_lineage,
    load_targeted_evidence_attribution,
    load_stable_truth_score_delta,
)


@app.command("snapshot-truth-state")
def snapshot_truth_state_command(
    name: Annotated[str, typer.Option("--name")] = "before_stage33",
) -> None:
    """Snapshot current truth state for lineage comparison."""
    dest = snapshot_truth_state(name=name)
    typer.echo(f"Snapshot saved to: {dest}")


@app.command("attribute-targeted-evidence")
def attribute_targeted_evidence_command(
    targeted: Annotated[Path, typer.Option("--targeted")] = Path("examples/real_signal_samples_stage33.csv"),
) -> None:
    """Attribute targeted signals through the pipeline (raw->pain->cluster->group)."""
    attributions = attribute_targeted_evidence(targeted_path=targeted)
    from collections import Counter
    counts = Counter(a.attribution_status for a in attributions)
    typer.echo(
        f"Attribution: {len(attributions)} signals | "
        f"expected={counts.get('attributed_to_expected_group',0)} | "
        f"related={counts.get('attributed_to_related_group',0)} | "
        f"lost_extraction={counts.get('lost_in_extraction',0)} | "
        f"lost_merge={counts.get('lost_in_merge',0)}"
    )
    write_targeted_evidence_attribution(attributions)
    typer.echo("Written -> data/processed/targeted_evidence_attribution.jsonl")


@app.command("match-candidate-lineage")
def match_candidate_lineage_command(
    before_snapshot: Annotated[
        Path, typer.Option("--before-snapshot")
    ] = Path("outputs/archive/before_stage33"),
) -> None:
    """Match before/after truth candidates to establish lineage."""
    import json
    lineage_baseline_quality = "full"

    if before_snapshot.exists():
        before_scores = load_snapshot_truth_scores(before_snapshot)
        typer.echo(f"Loaded {len(before_scores)} before scores from snapshot: {before_snapshot}")
    else:
        # Fallback: use truth_score_deltas to reconstruct before scores
        typer.echo(f"WARNING: Snapshot not found at {before_snapshot}, using delta report as fallback")
        lineage_baseline_quality = "partial"
        delta_path = Path("data/processed/truth_score_deltas.jsonl")
        before_scores = []
        if delta_path.exists():
            for line in delta_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    d = json.loads(line)
                    if d.get("before_truth_score") is not None:
                        before_scores.append({
                            "truth_score_id": None,
                            "source_group_id": d.get("source_group_id", ""),
                            "group_title_zh": d.get("group_title_zh", ""),
                            "truth_score": d.get("before_truth_score"),
                            "truth_level": d.get("before_truth_level"),
                            "recommended_next_action": d.get("before_next_action"),
                            "personas": [],
                            "domain_tags": [],
                        })
                except Exception:
                    pass
        typer.echo(f"Reconstructed {len(before_scores)} before scores from delta report")

    after_scores = load_current_truth_scores()
    typer.echo(f"Loaded {len(after_scores)} after scores")

    attributions = load_targeted_evidence_attribution()
    lineages = match_candidate_lineage(before_scores, after_scores, attributions)
    write_candidate_lineage(lineages)

    from collections import Counter
    sc = Counter(l.match_strength for l in lineages)
    typer.echo(
        f"Lineage: {len(lineages)} | strong={sc.get('strong',0)} | weak={sc.get('weak',0)} | "
        f"split={sc.get('split',0)} | merged={sc.get('merged',0)} | "
        f"unmatched={sc.get('unmatched',0)} | missing_baseline={sc.get('missing_baseline',0)}"
    )
    typer.echo(f"lineage_baseline_quality: {lineage_baseline_quality}")
    typer.echo("Written -> data/processed/candidate_lineage.jsonl")


@app.command("build-stable-truth-delta")
def build_stable_truth_delta_command() -> None:
    """Compute stable truth score delta from lineage."""
    lineages = load_candidate_lineage()
    if not lineages:
        typer.echo("No lineage data. Run match-candidate-lineage first.")
        raise typer.Exit(1)
    stable_deltas = compute_stable_deltas(lineages)
    write_stable_truth_score_delta(stable_deltas)
    from collections import Counter
    cc = Counter(d.delta_confidence for d in stable_deltas)
    typer.echo(
        f"Stable deltas: {len(stable_deltas)} | "
        f"high={cc.get('high',0)} | medium={cc.get('medium',0)} | low={cc.get('low',0)}"
    )
    typer.echo("Written -> data/processed/stable_truth_score_delta.jsonl")


@app.command("build-lineage-reports")
def build_lineage_reports_command() -> None:
    """Build all Stage 3.4 lineage reports."""
    lineages = load_candidate_lineage()
    attributions = load_targeted_evidence_attribution()
    stable_deltas = load_stable_truth_score_delta()

    build_candidate_lineage_report(lineages)
    typer.echo("Built -> outputs/candidate_lineage_report.md")

    build_targeted_evidence_attribution_report(attributions)
    typer.echo("Built -> outputs/targeted_evidence_attribution_report.md")

    build_stable_truth_score_delta_report(stable_deltas)
    typer.echo("Built -> outputs/stable_truth_score_delta_report.md")


@app.command("run-stage34")
def run_stage34(
    before_snapshot: Annotated[
        Path, typer.Option("--before-snapshot")
    ] = Path("outputs/archive/before_stage33"),
    targeted: Annotated[
        Path, typer.Option("--targeted")
    ] = Path("examples/real_signal_samples_stage33.csv"),
) -> None:
    """Stage 3.4: Candidate Lineage & Targeted Evidence Attribution."""
    import json
    typer.echo("Stage 3.4 starting: Candidate Lineage & Targeted Evidence Attribution")

    # Step 1: attribute evidence
    typer.echo("Step 1: Attributing targeted evidence through pipeline...")
    attributions = attribute_targeted_evidence(targeted_path=targeted)
    from collections import Counter
    attr_counts = Counter(a.attribution_status for a in attributions)
    write_targeted_evidence_attribution(attributions)
    typer.echo(
        f"  Attribution: expected={attr_counts.get('attributed_to_expected_group',0)} | "
        f"related={attr_counts.get('attributed_to_related_group',0)} | "
        f"lost_extraction={attr_counts.get('lost_in_extraction',0)} | "
        f"lost_merge={attr_counts.get('lost_in_merge',0)}"
    )

    # Step 2: load before/after scores
    lineage_baseline_quality = "full"
    if before_snapshot.exists():
        before_scores = load_snapshot_truth_scores(before_snapshot)
        typer.echo(f"Step 2: Loaded {len(before_scores)} before scores from snapshot")
    else:
        lineage_baseline_quality = "partial"
        typer.echo(f"Step 2: No snapshot at {before_snapshot}, using delta report fallback")
        before_scores = []
        delta_path = Path("data/processed/truth_score_deltas.jsonl")
        if delta_path.exists():
            for line in delta_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    d = json.loads(line)
                    if d.get("before_truth_score") is not None:
                        before_scores.append({
                            "truth_score_id": None,
                            "source_group_id": d.get("source_group_id", ""),
                            "group_title_zh": d.get("group_title_zh", ""),
                            "truth_score": d.get("before_truth_score"),
                            "truth_level": d.get("before_truth_level"),
                            "recommended_next_action": d.get("before_next_action"),
                            "personas": [],
                            "domain_tags": [],
                        })
                except Exception:
                    pass
        typer.echo(f"  Reconstructed {len(before_scores)} before scores")

    after_scores = load_current_truth_scores()
    typer.echo(f"  After scores: {len(after_scores)}")

    # Step 3: match lineage
    typer.echo("Step 3: Matching candidate lineage...")
    lineages = match_candidate_lineage(before_scores, after_scores, attributions)
    write_candidate_lineage(lineages)
    lc = Counter(l.match_strength for l in lineages)
    typer.echo(
        f"  Lineage: strong={lc.get('strong',0)} weak={lc.get('weak',0)} "
        f"split={lc.get('split',0)} merged={lc.get('merged',0)} "
        f"unmatched={lc.get('unmatched',0)} missing_baseline={lc.get('missing_baseline',0)}"
    )

    # Step 4: stable delta
    typer.echo("Step 4: Computing stable truth score delta...")
    stable_deltas = compute_stable_deltas(lineages)
    write_stable_truth_score_delta(stable_deltas)
    cc = Counter(d.delta_confidence for d in stable_deltas)
    typer.echo(f"  Stable deltas: high={cc.get('high',0)} medium={cc.get('medium',0)} low={cc.get('low',0)}")

    # Step 5: build reports
    typer.echo("Step 5: Building lineage reports...")
    build_candidate_lineage_report(lineages, lineage_baseline_quality=lineage_baseline_quality)
    build_targeted_evidence_attribution_report(attributions)
    build_stable_truth_score_delta_report(stable_deltas)
    typer.echo("Built -> outputs/candidate_lineage_report.md")
    typer.echo("Built -> outputs/targeted_evidence_attribution_report.md")
    typer.echo("Built -> outputs/stable_truth_score_delta_report.md")

    # Step 6: update batch summary
    build_batch_summary_report()
    typer.echo("Updated -> outputs/batch_summary_report.md")

    proceed = [d for d in stable_deltas if d.recommended_next_action == "proceed_to_fit_scoring"]
    typer.echo(
        f"Stage 3.4 complete: lineage_baseline_quality={lineage_baseline_quality} | "
        f"lineages={len(lineages)} | stable_proceed_to_fit={len(proceed)}"
    )


def main() -> None:
    app()


if __name__ == "__main__":
    main()




# ── Stage 3.5 commands ──────────────────────────────────────────────────────

@app.command("run-stage35")
def run_stage35_command(
    snapshot_name: Annotated[
        str, typer.Option("--snapshot-name")
    ] = "before_stage35",
    filled: Annotated[
        Path, typer.Option("--filled")
    ] = Path("examples/real_signal_samples_stage35.csv"),
) -> None:
    """Stage 3.5: Snapshot-first targeted evidence expansion (no LLM)."""
    from demand_radar.stage35.stage35_pipeline import run_stage35
    typer.echo("Stage 3.5 starting (template + validate + gate)...")
    result = run_stage35(snapshot_name=snapshot_name, filled_sample_path=str(filled))
    gate = result.get("stage4_gate_status", "not_run")
    cands = result.get("selected_candidates", 0)
    typer.echo(f"  Stage 3.5 done: selected_candidates={cands} stage4_gate={gate}")
    typer.echo("  Reports: outputs/stage35_targeted_expansion_report.md")
    typer.echo("          outputs/stage35_stage4_gate_report.md")


@app.command("run-stage35-full")
def run_stage35_full_command(
    snapshot_name: Annotated[
        str, typer.Option("--snapshot-name")
    ] = "before_stage35",
    filled: Annotated[
        Path, typer.Option("--filled")
    ] = Path("examples/real_signal_samples_stage35.csv"),
) -> None:
    """Stage 3.5 full: LLM rerun + lineage + gate (requires API key)."""
    import os
    from demand_radar.stage35.stage35_pipeline import run_stage35
    if not os.environ.get("DEMAND_RADAR_LLM_API_KEY"):
        typer.echo("ERROR: DEMAND_RADAR_LLM_API_KEY not set. run-stage35-full requires an LLM API key.", err=True)
        raise typer.Exit(code=1)
    typer.echo("WARNING: run-stage35-full will trigger LLM API calls. Press Ctrl+C to abort.")
    # Step 1: run-stage35 (snapshot + template + validate)
    result = run_stage35(snapshot_name=snapshot_name, filled_sample_path=str(filled))
    if result.get("status") == "no_candidates":
        typer.echo("Aborted: no eligible candidates.")
        raise typer.Exit(code=1)
    # Step 2: rebuild combined input
    from demand_radar.targeted_expansion.combined_input_builder import build_combined_input
    base = Path("examples/combined_signal_samples_stage33.csv")
    if not base.exists():
        base = Path("examples/real_signal_samples_stage26.csv")
    stats = build_combined_input(
        base_path=str(base),
        targeted_path=str(filled),
        validation_path="data/processed/stage35_targeted_signal_validation.jsonl",
        output_path="examples/combined_signal_samples_stage35.csv",
    )
    typer.echo(f"  Combined input: {stats.get(chr(39)+'combined_rows'+chr(39), 0)} rows")
    # Step 3: run-stage26
    typer.echo("  Running stage26...")
    run_stage26(input=Path("examples/combined_signal_samples_stage35.csv"))
    # Step 4: run-stage29c
    typer.echo("  Running stage29c (LLM)...")
    run_stage29c(
        input=Path("examples/combined_signal_samples_stage35.csv"),
        force_rerun=True,
    )
    # Step 5: run-stage3
    typer.echo("  Running stage3...")
    run_truth_scoring_command(source="calibrated_llm")
    # Step 6: run-stage32
    typer.echo("  Running stage32...")
    run_stage32_command(source="calibrated_llm")
    # Step 7: run-stage34 with before snapshot
    typer.echo("  Running stage34...")
    run_stage34(before_snapshot=Path(f"outputs/archive/{snapshot_name}"))
    # Step 8: final gate
    typer.echo("  Evaluating Stage 4 gate...")
    from demand_radar.stage35.stage35_gate import evaluate_stage4_gate
    from demand_radar.lineage.lineage_store import load_stable_truth_score_delta
    deltas = [d.model_dump() for d in load_stable_truth_score_delta()]
    gate = evaluate_stage4_gate(deltas, lineage_baseline_quality="full")
    from demand_radar.stage35.stage35_report import build_stage35_gate_report
    build_stage35_gate_report(gate.model_dump())
    typer.echo(f"Stage 3.5 full complete. Gate status: {gate.status}")
    typer.echo("  Report: outputs/stage35_stage4_gate_report.md")


@app.command("select-stage35-candidates")
def select_stage35_candidates_command() -> None:
    """Select Stage 3.5 target candidates from truth_scores."""
    from demand_radar.stage35.stage35_candidate_selector import select_stage35_candidates
    candidates = select_stage35_candidates()
    typer.echo(f"Selected {len(candidates)} Stage 3.5 candidates:")
    for c in candidates:
        typer.echo(f"  [{c.priority_rank}] {c.group_title_zh[:60]} (score={c.current_truth_score})")


@app.command("build-stage35-template")
def build_stage35_template_command() -> None:
    """Build Stage 3.5 targeted signal template CSV."""
    from demand_radar.stage35.stage35_template_builder import build_stage35_template
    rows = build_stage35_template()
    typer.echo(f"Template built: {len(rows)} rows -> examples/stage35_targeted_signal_template.csv")


@app.command("validate-stage35-signals")
def validate_stage35_signals_command(
    input: Annotated[
        Path, typer.Option("--input")
    ] = Path("examples/real_signal_samples_stage35.csv"),
) -> None:
    """Validate Stage 3.5 filled signals."""
    from demand_radar.stage35.stage35_validator import validate_stage35_signals
    if not input.exists():
        typer.echo(f"File not found: {input}", err=True)
        raise typer.Exit(code=1)
    results = validate_stage35_signals(input)
    valid_n = sum(1 for r in results if r.get("status") == "valid")
    warn_n = sum(1 for r in results if r.get("status") == "warning")
    inv_n = sum(1 for r in results if r.get("status") == "invalid")
    typer.echo(f"Validation: total={len(results)} valid={valid_n} warning={warn_n} invalid={inv_n}")


@app.command("build-real-evidence-template")
def build_real_evidence_template_command() -> None:
    """Generate the real evidence pack CSV template."""
    from demand_radar.real_evidence.real_evidence_validator import generate_template
    out = generate_template()
    typer.echo(f"Template generated: {out}")


@app.command("validate-real-evidence-pack")
def validate_real_evidence_pack_command(
    input: Annotated[
        _Path, typer.Option("--input")
    ] = _Path("examples/real_evidence_pack_ai_investment_tracking.csv"),
) -> None:
    """Validate the filled real evidence pack CSV."""
    from demand_radar.real_evidence.real_evidence_validator import validate_real_evidence_pack
    if not input.exists():
        typer.echo(f"File not found: {input}", err=True)
        raise typer.Exit(code=1)
    items_path = _Path("data/processed/real_evidence_items.jsonl")
    validation_path = _Path("data/processed/real_evidence_validation.jsonl")
    items, validations = validate_real_evidence_pack(input, items_path, validation_path)
    valid_n = sum(1 for v in validations if v.status == "valid")
    warn_n = sum(1 for v in validations if v.status == "warning")
    inv_n = sum(1 for v in validations if v.status == "invalid")
    excl_n = sum(1 for v in validations if v.status == "excluded")
    typer.echo(
        f"Validation complete: total={len(validations)} "
        f"valid={valid_n} warning={warn_n} invalid={inv_n} excluded={excl_n}"
    )
    typer.echo(f"Items saved: {items_path}")
    typer.echo(f"Validations saved: {validation_path}")


@app.command("run-real-evidence-pack")
def run_real_evidence_pack_command(
    input: Annotated[
        _Path, typer.Option("--input")
    ] = _Path("examples/real_evidence_pack_ai_investment_tracking.csv"),
) -> None:
    """Convert validated real evidence to signal CSV for pipeline."""
    from demand_radar.real_evidence.real_evidence_store import load_real_evidence_items, load_real_evidence_validations
    from demand_radar.real_evidence.real_evidence_pipeline import convert_to_signal_csv
    items = load_real_evidence_items()
    validations = load_real_evidence_validations()
    if not items:
        typer.echo("No real evidence items found. Run validate-real-evidence-pack first.")
        raise typer.Exit(code=0)
    includeable = [i for i, v in zip(items, validations) if v.include_in_pipeline]
    out = convert_to_signal_csv(includeable)
    typer.echo(f"Signal CSV generated: {out} ({len(includeable)} items)")


@app.command("build-real-evidence-report")
def build_real_evidence_report_command() -> None:
    """Build the real evidence pack report."""
    from demand_radar.real_evidence.real_evidence_store import load_real_evidence_items, load_real_evidence_validations
    from demand_radar.real_evidence.calibration_report import build_real_evidence_pack_report
    items = load_real_evidence_items()
    validations = load_real_evidence_validations()
    out = build_real_evidence_pack_report(items, validations)
    typer.echo(f"Report: {out}")


@app.command("build-calibration-report")
def build_calibration_report_command() -> None:
    """Build the calibration report and recommendations."""
    from demand_radar.real_evidence.real_evidence_store import load_calibration_reviews, load_calibration_findings
    from demand_radar.real_evidence.calibration_report import (
        build_calibration_report,
        build_prompt_skill_recommendations,
    )
    reviews = load_calibration_reviews()
    findings = load_calibration_findings()
    out1 = build_calibration_report(reviews)
    out2 = build_prompt_skill_recommendations(reviews, findings)
    typer.echo(f"Calibration report: {out1}")
    typer.echo(f"Recommendations: {out2}")


@app.command("run-stage-r1")
def run_stage_r1_command(
    filled_input: Annotated[
        _Path, typer.Option("--input")
    ] = _Path("examples/real_evidence_pack_ai_investment_tracking.csv"),
    skip_llm: Annotated[bool, typer.Option("--skip-llm/--no-skip-llm")] = True,
) -> None:
    """Run Stage R1: Real Evidence Pack & Calibration Loop."""
    from demand_radar.real_evidence.real_evidence_pipeline import run_stage_r1
    result = run_stage_r1(filled_path=filled_input, skip_llm=skip_llm)
    if not result["filled_file_exists"]:
        typer.echo(
            "[Stage R1] 真实证据包尚未填写。\n"
            f"请先填写：{filled_input}\n"
            "使用 demand-radar build-real-evidence-template 生成模板。"
        )
        raise typer.Exit(code=0)
    typer.echo(
        f"[Stage R1] Complete. items={result['items']} "
        f"valid={result['valid']} warning={result['warning']} "
        f"invalid={result['invalid']} excluded={result['excluded']}"
    )
    if result["signal_csv_generated"]:
        typer.echo("Signal CSV: examples/real_evidence_signals_ai_investment_tracking.csv")
    for r in result.get("reports_generated", []):
        typer.echo(f"Report: {r}")

@app.command("run-acquisition")
def run_acquisition_command(
    domain: Annotated[str, typer.Option("--domain")] = "ai_investment_tracking",
    max_items: Annotated[int, typer.Option("--max-items")] = 20,
) -> None:
    """Run acquisition for a domain using opc-foundation connectors."""
    from demand_radar.acquisition.acquisition_pipeline import run_acquisition
    from demand_radar.acquisition.acquisition_report import build_acquisition_report
    typer.echo(f"[run-acquisition] domain={domain} max_items={max_items}")
    try:
        summary, candidates = run_acquisition(domain_id=domain, max_items_per_query=max_items)
        build_acquisition_report(summary, candidates)
        typer.echo(
            f"Acquisition complete: raw={summary.raw_signal_count} "
            f"unique={summary.unique_signal_count} "
            f"valid_candidates={summary.valid_candidate_count}"
        )
        if summary.errors:
            typer.echo(f"Errors: {len(summary.errors)} (see acquisition_report.md)")
        typer.echo("Report: outputs/acquisition/acquisition_report.md")
    except Exception as exc:
        typer.echo(f"[run-acquisition] Error: {exc}", err=True)
        raise typer.Exit(code=1)


@app.command("build-evidence-pack-draft")
def build_evidence_pack_draft_command(
    domain: Annotated[str, typer.Option("--domain")] = "ai_investment_tracking",
) -> None:
    """Build evidence pack draft CSV from acquisition candidates."""
    from demand_radar.acquisition.acquisition_store import load_evidence_candidates
    from demand_radar.acquisition.evidence_pack_draft_builder import build_evidence_pack_draft
    from demand_radar.acquisition.acquisition_report import build_evidence_pack_draft_report
    candidates = load_evidence_candidates()
    if not candidates:
        typer.echo("No evidence candidates found. Run demand-radar run-acquisition first.")
        raise typer.Exit(code=0)
    out = build_evidence_pack_draft(candidates)
    valid = [c for c in candidates if c.include_in_evidence_pack]
    build_evidence_pack_draft_report(candidates, out)
    typer.echo(f"Draft CSV: {out} ({len(valid)} items)")
    typer.echo("Report: outputs/acquisition/evidence_pack_draft_report.md")


@app.command("run-radar")
def run_radar_command(
    domain: Annotated[str, typer.Option("--domain")] = "ai_investment_tracking",
    max_items: Annotated[int, typer.Option("--max-items")] = 20,
) -> None:
    """Run full Demand Radar pipeline: acquisition -> draft -> R1 validation -> report."""
    from demand_radar.acquisition.radar_pipeline import run_radar
    typer.echo(f"[run-radar] domain={domain}")
    try:
        result = run_radar(domain_id=domain)
        typer.echo(
            f"Radar complete: raw={result.raw_signals} unique={result.unique_signals} "
            f"valid_candidates={result.valid_candidates}"
        )
        if result.draft_csv:
            typer.echo(f"Draft CSV: {result.draft_csv}")
        typer.echo(f"R1 validation: {result.r1_validation_summary}")
        typer.echo("Radar report: outputs/radar/radar_report.md")
    except Exception as exc:
        typer.echo(f"[run-radar] Error: {exc}", err=True)
        raise typer.Exit(code=1)


@app.command("build-acquisition-report")
def build_acquisition_report_command(
    domain: Annotated[str, typer.Option("--domain")] = "ai_investment_tracking",
) -> None:
    """Build acquisition report from stored candidates."""
    from demand_radar.acquisition.acquisition_store import load_evidence_candidates, load_run_log
    from demand_radar.acquisition.acquisition_report import build_acquisition_report
    from demand_radar.acquisition.acquisition_schema import AcquisitionRunSummary
    candidates = load_evidence_candidates()
    run_logs = load_run_log()
    if not run_logs:
        typer.echo("No acquisition run log found. Run demand-radar run-acquisition first.")
        raise typer.Exit(code=0)
    summary = AcquisitionRunSummary(**run_logs[-1])
    out = build_acquisition_report(summary, candidates)
    typer.echo(f"Report: {out}")

@app.command("run-mvp-b")
def run_mvp_b_command(
    domain: Annotated[str, typer.Option("--domain")] = "ai_investment_tracking",
    max_items: Annotated[int | None, typer.Option("--max-items")] = None,
    fake_llm: Annotated[bool, typer.Option("--fake-llm/--no-fake-llm")] = False,
    no_cache: Annotated[bool, typer.Option("--no-cache")] = False,
) -> None:
    """Run MVP-B: domain relevance filter + pain extraction on acquired candidates."""
    from demand_radar.mvp_b.mvp_b_pipeline import run_mvp_b
    from demand_radar.semantic_merge.llm_client import make_llm_client, FakeLLMClient
    import yaml, os
    typer.echo(f"[run-mvp-b] domain={domain} max_items={max_items} fake_llm={fake_llm}")
    llm_client = None
    if fake_llm:
        import json
        fake_response = json.dumps({
            "candidate_id": "cand_fake",
            "should_extract": True,
            "reject_reason": None,
            "persona": "investment researcher",
            "persona_confidence": 0.8,
            "workflow_stage": "company_tracking",
            "job_to_be_done": "Track AI startups efficiently",
            "pain_type": "manual_workflow",
            "pain_description_zh": "手动追踪 AI 创业公司耗时低效",
            "evidence_quote": "We spend hours manually tracking AI startups",
            "current_solution": "spreadsheet",
            "paid_alternative": None,
            "business_impact": "3 hours per week wasted",
            "time_cost_signal": "3 hours per week",
            "budget_signal": None,
            "commercial_signal_type": "manual_labor_cost",
            "evidence_strength": "medium",
            "confidence": 0.75,
            "reasoning_summary_zh": "Fake extraction for testing"
        })
        llm_client = FakeLLMClient(default=fake_response)
    else:
        provider = os.environ.get("DEMAND_RADAR_LLM_PROVIDER", "openai_compatible")
        llm_conf = {"llm": {
            "base_url_env": "DEMAND_RADAR_LLM_BASE_URL",
            "api_key_env": "DEMAND_RADAR_LLM_API_KEY",
            "model": os.environ.get("DEMAND_RADAR_LLM_MODEL", "claude-sonnet-4-6"),
        }}
        try:
            llm_client = make_llm_client(provider, llm_conf)
        except Exception as exc:
            typer.echo(f"LLM client init failed: {exc}. Running without LLM (rule-only).", err=True)
    try:
        result = run_mvp_b(domain_id=domain, max_items=max_items, llm_client=llm_client)
        typer.echo(
            f"MVP-B complete: candidates={result.candidates_processed} "
            f"include={result.include_count} exclude={result.exclude_count} "
            f"extracted={result.should_extract_count} strong={result.strong_count}"
        )
        typer.echo(f"R1 before: {result.r1_before}")
        typer.echo(f"R1 after: {result.r1_after}")
        if result.filled_csv:
            typer.echo(f"Filled CSV: {result.filled_csv}")
        if result.errors:
            typer.echo(f"Errors: {result.errors[:3]}", err=True)
    except Exception as exc:
        typer.echo(f"[run-mvp-b] Error: {exc}", err=True)
        raise typer.Exit(code=1)


@app.command("run-domain-relevance")
def run_domain_relevance_command(
    domain: Annotated[str, typer.Option("--domain")] = "ai_investment_tracking",
    max_items: Annotated[int | None, typer.Option("--max-items")] = None,
) -> None:
    """Run domain relevance filter (rule-based) on evidence candidates."""
    import json
    from pathlib import Path as _Path2
    from demand_radar.mvp_b.domain_relevance_filter import run_domain_relevance_filter
    from demand_radar.mvp_b.mvp_b_store import write_relevance_results
    _cands_p = _Path2("data/processed/acquisition/evidence_candidates.jsonl")
    cands = []
    if _cands_p.exists():
        for line in _cands_p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    cands.append(json.loads(line))
                except Exception:
                    pass
    if max_items:
        cands = cands[:max_items]
    results = run_domain_relevance_filter(cands)
    write_relevance_results(results)
    inc = sum(1 for r in results if r.relevance_decision == "include")
    exc = sum(1 for r in results if r.relevance_decision == "exclude")
    unc = sum(1 for r in results if r.relevance_decision == "uncertain")
    typer.echo(f"Domain relevance: {len(results)} candidates | include={inc} uncertain={unc} exclude={exc}")


@app.command("run-pain-extraction")
def run_pain_extraction_command(
    domain: Annotated[str, typer.Option("--domain")] = "ai_investment_tracking",
    max_items: Annotated[int | None, typer.Option("--max-items")] = None,
    fake_llm: Annotated[bool, typer.Option("--fake-llm/--no-fake-llm")] = False,
) -> None:
    """Run pain extraction LLM on domain-relevant candidates."""
    import os
    from demand_radar.mvp_b.mvp_b_store import load_relevance_dicts, load_pain_dicts, write_pain_items
    from demand_radar.mvp_b.pain_extraction_runner import run_pain_extraction
    from demand_radar.acquisition.acquisition_store import load_evidence_candidates
    from demand_radar.semantic_merge.llm_client import make_llm_client, FakeLLMClient
    candidates = [c.model_dump() for c in load_evidence_candidates()]
    rel_dicts = load_relevance_dicts()
    if max_items:
        candidates = candidates[:max_items]
    llm_client = None
    if fake_llm:
        llm_client = FakeLLMClient(default='{"candidate_id":"x","should_extract":false,"reject_reason":"fake","evidence_strength":"reject","confidence":0.0}')
    else:
        provider = os.environ.get("DEMAND_RADAR_LLM_PROVIDER", "openai_compatible")
        llm_conf = {"llm": {"base_url_env": "DEMAND_RADAR_LLM_BASE_URL", "api_key_env": "DEMAND_RADAR_LLM_API_KEY", "model": os.environ.get("DEMAND_RADAR_LLM_MODEL", "claude-sonnet-4-6")}}
        try:
            llm_client = make_llm_client(provider, llm_conf)
        except Exception as exc:
            typer.echo(f"LLM init error: {exc}", err=True)
    items = run_pain_extraction(candidates, rel_dicts, llm_client=llm_client, max_items=max_items)
    write_pain_items(items)
    extracted_n = sum(1 for p in items if p.should_extract)
    typer.echo(f"Pain extraction: {len(items)} items | extracted={extracted_n}")


@app.command("fill-evidence-pack")
def fill_evidence_pack_command(
    domain: Annotated[str, typer.Option("--domain")] = "ai_investment_tracking",
) -> None:
    """Fill evidence pack draft CSV with extracted pain fields."""
    from demand_radar.mvp_b.evidence_pack_filler import fill_evidence_pack
    from demand_radar.mvp_b.mvp_b_store import load_relevance_dicts, load_pain_dicts
    rel_dicts = load_relevance_dicts()
    pain_dicts = load_pain_dicts()
    out = fill_evidence_pack(relevance_dicts=rel_dicts, pain_dicts=pain_dicts)
    typer.echo(f"Filled evidence pack: {out}")


@app.command("build-mvp-b-report")
def build_mvp_b_report_command(
    domain: Annotated[str, typer.Option("--domain")] = "ai_investment_tracking",
) -> None:
    """Build all MVP-B reports from stored data."""
    from demand_radar.mvp_b.mvp_b_store import load_relevance_dicts, load_pain_dicts
    from demand_radar.mvp_b.mvp_b_report import (
        build_domain_relevance_report, build_pain_extraction_report,
        build_top_pain_signals_report, build_mvp_b_summary_report,
    )
    rel = load_relevance_dicts()
    pain = load_pain_dicts()
    r1 = build_domain_relevance_report(rel)
    r2 = build_pain_extraction_report(pain)
    r3 = build_top_pain_signals_report(pain)
    r4 = build_mvp_b_summary_report(rel, pain, {}, {})
    typer.echo(f"Reports: {r1} | {r2} | {r3} | {r4}")

@app.command("run-mvp-c")
def run_mvp_c_command() -> None:
    """Run MVP-C: generate pain signal review reports (no UI)."""
    from demand_radar.mvp_c.mvp_c_pipeline import run_mvp_c
    result = run_mvp_c()
    typer.echo(f"[run-mvp-c] total={result.total_pain_items} reviewed={result.reviewed_count} unreviewed={result.unreviewed_count}")
    typer.echo(f"[run-mvp-c] true_pain={result.true_pain_count} pursue={result.pursue_count} findings={result.findings_count}")
    typer.echo(f"[run-mvp-c] engineering={result.engineering_acceptance} product={result.product_acceptance}")
    if result.errors:
        for e in result.errors:
            typer.echo(f"[run-mvp-c] ERROR: {e}", err=True)


@app.command("summarize-pain-reviews")
def summarize_pain_reviews_command() -> None:
    """Print pain signal review summary to console."""
    from demand_radar.mvp_c.review_service import ReviewService
    svc = ReviewService()
    summary = svc.get_summary()
    typer.echo(f"Total: {summary.total_pain_items} | Reviewed: {summary.reviewed_count} | Unreviewed: {summary.unreviewed_count}")
    typer.echo(f"True pain: {summary.true_pain_count} | False: {summary.false_pain_count}")
    typer.echo(f"Actions - pursue: {summary.pursue_count} | watch: {summary.watch_count} | reject: {summary.reject_count} | needs_more: {summary.needs_more_evidence_count}")
    typer.echo(f"Commercial - high: {summary.commercial_high_count} | medium: {summary.commercial_medium_count} | low: {summary.commercial_low_count} | unclear: {summary.commercial_unclear_count}")
    if summary.top_error_labels:
        typer.echo(f"Top errors: {summary.top_error_labels}")


@app.command("build-mvp-c-report")
def build_mvp_c_report_command() -> None:
    """Build all MVP-C reports from stored reviews."""
    from demand_radar.mvp_c.mvp_c_pipeline import run_mvp_c
    result = run_mvp_c()
    typer.echo(f"[build-mvp-c-report] Reports generated. engineering={result.engineering_acceptance} product={result.product_acceptance}")
