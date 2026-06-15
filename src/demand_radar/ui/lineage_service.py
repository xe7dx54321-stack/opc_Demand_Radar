"""UI service for Stage 3.4 lineage."""
from __future__ import annotations
from demand_radar.lineage.lineage_store import (
    load_candidate_lineage,
    load_targeted_evidence_attribution,
    load_stable_truth_score_delta,
)


def get_candidate_lineages():
    return load_candidate_lineage()


def get_targeted_evidence_attributions():
    return load_targeted_evidence_attribution()


def get_stable_truth_score_deltas():
    return load_stable_truth_score_delta()
