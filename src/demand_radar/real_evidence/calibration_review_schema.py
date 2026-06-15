"""Stage R1: calibration_review_schema - PromptCalibrationFinding."""
from __future__ import annotations
from pydantic import BaseModel


class PromptCalibrationFinding(BaseModel):
    finding_id: str
    finding_type: str
    # extraction_error | merge_error | rubric_gap | skill_gap | source_weight_error | rejection_rule_gap
    description_zh: str
    affected_items: list[str] = []
    suggested_fix_zh: str
    priority: str = "medium"  # high | medium | low
    created_at: str