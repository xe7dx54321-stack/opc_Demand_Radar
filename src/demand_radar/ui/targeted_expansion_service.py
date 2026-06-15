"""UI service for Stage 3.3."""
from __future__ import annotations
from demand_radar.targeted_expansion.expansion_store import load_expansion_summary,load_truth_score_deltas
from demand_radar.targeted_expansion.targeted_validator import load_validations
def get_expansion_summary(): return load_expansion_summary()
def get_targeted_validations(): return load_validations()
def get_truth_score_deltas(): return load_truth_score_deltas()
