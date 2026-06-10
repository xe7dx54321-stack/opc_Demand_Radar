from demand_radar.batch.batch_schema import BatchSummary, Stage3Readiness


def test_batch_summary_can_be_created_with_rates() -> None:
    summary = BatchSummary(
        batch_id="batch_stage26_ai_research",
        raw_signals=10,
        normalized_signals=9,
        pain_points=7,
        quarantined_items=1,
        demand_clusters=5,
        singleton_clusters=3,
        merge_candidates=4,
        reviewed_groups=1,
        calibration_reviews=2,
        cluster_reviews=1,
        merge_reviews=1,
        extraction_yield=0.7778,
        quarantine_rate=0.1,
        singleton_rate=0.6,
        merge_candidate_rate=0.8,
        good_extractions=1,
        weak_extractions=1,
    )

    assert summary.batch_id == "batch_stage26_ai_research"
    assert summary.created_at
    assert summary.extraction_yield == 0.7778
    assert summary.good_extractions == 1


def test_stage3_readiness_schema_records_mechanical_judgement() -> None:
    readiness = Stage3Readiness(
        sample_size_ok=True,
        pain_volume_ok=True,
        group_volume_ok=False,
        clustering_convergence_ok=True,
        ready_for_truth_scoring="partial",
        recommendation="继续补充人工确认需求组后再进入 Truth Scoring。",
    )

    assert readiness.ready_for_truth_scoring == "partial"
    assert readiness.recommendation
