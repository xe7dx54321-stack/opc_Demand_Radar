"""Convert RawSignal -> EvidenceCandidate."""
from __future__ import annotations
from opc_foundation.signals.raw_signal_schema import RawSignal
from opc_foundation.run.id_generator import new_id
from opc_foundation.run.time_utils import utcnow_iso
from .acquisition_schema import EvidenceCandidate

_WEIGHT_MAP = {
    "product_review": 0.95,
    "community_discussion": 0.90,
    "github_issue": 0.90,
    "interview_note": 0.90,
    "case_study": 0.75,
    "pricing_page": 0.70,
    "job_posting": 0.70,
    "manual_url": 0.70,
    "rss": 0.55,
    "newsletter": 0.55,
    "blog_post": 0.45,
    "social_post": 0.40,
}

_PAY_KW = ["pricing", "cost", "$", "subscription", "pay", "paid", "budget", "purchase", "fee", "vendor"]
_WORK_KW = ["manual", "spreadsheet", "excel", "notion", "workaround", "hand", "outsource", "script"]
_TIME_KW = ["time", "hours", "days", "tedious", "slow", "inefficient", "waste", "delay"]
_FLOW_KW = ["research", "track", "monitor", "screen", "pipeline", "workflow", "sourcing", "due diligence"]


def _has(text: str, kws: list[str]) -> bool:
    lo = text.lower()
    return any(k in lo for k in kws)


def _detect_signal_types(raw_text: str, source_type: str) -> list[str]:
    types: list[str] = []
    if _has(raw_text, _PAY_KW):
        types.append("paid_signal")
    if _has(raw_text, _WORK_KW):
        types.append("workaround_signal")
    if _has(raw_text, _TIME_KW):
        types.append("time_cost_signal")
    if _has(raw_text, _FLOW_KW):
        types.append("workflow_signal")
    if source_type == "pricing_page":
        if "paid_signal" not in types:
            types.append("paid_signal")
    return types


def build_evidence_candidate(
    signal: RawSignal,
    domain_id: str,
    domain_title_zh: str,
    seen_url_hashes: set[str],
    seen_content_hashes: set[str],
) -> EvidenceCandidate:
    raw_text = signal.raw_text or ""
    errors: list[str] = []
    status = "valid"

    # Duplicate check
    url_hash = signal.url_hash
    content_hash = signal.content_hash
    is_dup = False
    if url_hash and url_hash in seen_url_hashes:
        is_dup = True
    elif content_hash and content_hash in seen_content_hashes:
        is_dup = True

    if is_dup:
        status = "duplicate"
    elif len(raw_text.strip()) < 80:
        status = "invalid"
        errors.append("raw_text too short (< 80 chars)")
    elif not signal.source_url and not signal.source_note:
        status = "invalid"
        errors.append("no source_url or source_note")

    if status == "valid":
        if url_hash:
            seen_url_hashes.add(url_hash)
        if content_hash:
            seen_content_hashes.add(content_hash)

    source_weight = _WEIGHT_MAP.get(signal.source_type, 0.50)
    detected = _detect_signal_types(raw_text, signal.source_type)

    include = status in ("valid", "warning")

    return EvidenceCandidate(
        candidate_id=new_id("cand_"),
        raw_signal_id=signal.signal_id,
        source_id=signal.source_id,
        source_type=signal.source_type,
        source_name=signal.source_name,
        source_url=signal.source_url,
        title=signal.title,
        raw_text=raw_text,
        domain_id=domain_id,
        domain_title_zh=domain_title_zh,
        collection_query=signal.collection_query,
        fetched_at=signal.fetched_at,
        source_weight=source_weight,
        validation_status=status,
        validation_reasons=errors,
        detected_signal_types=detected,
        include_in_evidence_pack=include,
        metadata=signal.metadata,
    )


def build_evidence_candidates(
    signals: list[RawSignal],
    domain_id: str,
    domain_title_zh: str,
) -> list[EvidenceCandidate]:
    seen_url: set[str] = set()
    seen_content: set[str] = set()
    return [
        build_evidence_candidate(sig, domain_id, domain_title_zh, seen_url, seen_content)
        for sig in signals
    ]
