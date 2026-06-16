"""Convert EvidenceCandidate -> RealEvidenceItem draft CSV."""
from __future__ import annotations
import csv
from pathlib import Path

from .acquisition_schema import EvidenceCandidate

_DRAFT_CSV_PATH = Path("examples/real_evidence_pack_ai_investment_tracking_draft.csv")

DRAFT_COLUMNS = [
    "evidence_id", "target_direction_id", "target_direction_title_zh",
    "source_url", "source_note", "source_name", "source_type",
    "source_author_or_org", "published_at", "observed_at", "language",
    "title", "raw_text", "evidence_quote",
    "persona", "persona_confidence", "workflow_stage", "pain_type",
    "evidence_type", "commercial_signal_type",
    "current_solution", "paid_alternative", "business_impact",
    "time_cost_signal", "budget_signal",
    "domain_tags", "collection_query", "collector_note",
    "is_synthetic", "exclude_from_scoring",
]


def _candidate_to_row(c: EvidenceCandidate) -> dict:
    domain_tags = c.domain_id
    evidence_type = ""
    if "paid_signal" in c.detected_signal_types:
        evidence_type = "paid_signal"
    elif "workaround_signal" in c.detected_signal_types:
        evidence_type = "workaround_signal"
    elif "time_cost_signal" in c.detected_signal_types:
        evidence_type = "business_impact_signal"
    elif "workflow_signal" in c.detected_signal_types:
        evidence_type = "pain_signal"

    exclude = "true" if c.validation_status == "invalid" else "false"

    return {
        "evidence_id": c.candidate_id,
        "target_direction_id": c.domain_id,
        "target_direction_title_zh": c.domain_title_zh,
        "source_url": c.source_url or "",
        "source_note": "",
        "source_name": c.source_name or "",
        "source_type": c.source_type,
        "source_author_or_org": "",
        "published_at": "",
        "observed_at": "",
        "language": "en",
        "title": c.title or "",
        "raw_text": c.raw_text,
        "evidence_quote": "",
        "persona": "",
        "persona_confidence": "",
        "workflow_stage": "",
        "pain_type": "",
        "evidence_type": evidence_type,
        "commercial_signal_type": "paid_tool" if "paid_signal" in c.detected_signal_types else "",
        "current_solution": "",
        "paid_alternative": "",
        "business_impact": "",
        "time_cost_signal": "",
        "budget_signal": "",
        "domain_tags": domain_tags,
        "collection_query": c.collection_query or "",
        "collector_note": f"auto-acquired via {c.source_type}",
        "is_synthetic": "false",
        "exclude_from_scoring": exclude,
    }


def build_evidence_pack_draft(
    candidates: list[EvidenceCandidate],
    output_path: Path | None = None,
    include_only_valid: bool = True,
) -> Path:
    out = output_path or _DRAFT_CSV_PATH
    out.parent.mkdir(parents=True, exist_ok=True)

    if include_only_valid:
        candidates = [c for c in candidates if c.include_in_evidence_pack]

    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=DRAFT_COLUMNS)
        writer.writeheader()
        for c in candidates:
            writer.writerow(_candidate_to_row(c))

    return out
