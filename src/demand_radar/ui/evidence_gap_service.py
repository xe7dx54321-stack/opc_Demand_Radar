"""UI helper service for Stage 3.2 Evidence Gap Analysis."""
from __future__ import annotations
from demand_radar.evidence_gap.evidence_gap_schema import EvidenceGapAnalysis, TargetedSignalCollectionPlan
from demand_radar.evidence_gap.evidence_gap_store import load_gap_analysis, load_collection_plans


def get_gap_analyses() -> list[EvidenceGapAnalysis]:
    return load_gap_analysis()


def get_collection_plans() -> list[TargetedSignalCollectionPlan]:
    return load_collection_plans()
