"""Stage 3.5 UI service."""
from __future__ import annotations
from demand_radar.stage35.stage35_store import (
    load_selected_candidates, load_run_summary, load_gate_result,
)
from demand_radar.stage35.stage35_validator import load_stage35_validations


def get_stage35_selected_candidates():
    return load_selected_candidates()


def get_stage35_run_summary():
    return load_run_summary()


def get_stage35_gate_result():
    return load_gate_result()


def get_stage35_validations():
    return load_stage35_validations()
