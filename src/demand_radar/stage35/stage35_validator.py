"""Stage 3.5 targeted signal validator (stricter than Stage 3.3)."""
from __future__ import annotations
import csv
from pathlib import Path
from demand_radar.state.raw_store import next_ids, utc_now_iso

_PAY_KW = [
    "\u4ed8\u8d39", "\u8ba2\u9605", "\u6536\u8d39", "\u9884\u7b97", "\u91c7\u8d2d",
    "\u8d2d\u4e70", "SaaS", "\u5e74\u8d39", "\u6708\u8d39", "\u5b9a\u4ef7",
    "\u5408\u540c", "\u62a5\u4ef7", "\u6536\u8d39\u8ba2\u9605",
    "price", "paid", "payment", "subscription", "budget", "cost", "fee", "purchase",
]
_WA_KW = [
    "\u4eba\u5de5", "\u624b\u5de5", "\u624b\u52a8", "\u8868\u683c", "Excel",
    "\u5185\u90e8\u7cfb\u7edf", "\u5916\u5305", "\u811a\u672c", "\u95ee\u540c\u4e8b",
    "\u5f53\u524d\u5de5\u5177", "\u73b0\u6709\u6d41\u7a0b", "\u66ff\u4ee3\u65b9\u6848",
    "manual", "spreadsheet", "workaround", "excel", "current tool", "existing",
]
_IMPACT_KW = [
    "\u65f6\u95f4", "\u4eba\u529b", "\u6548\u7387", "\u6d6a\u8d39", "\u9700\u8981\u591a\u957f",
    "\u5ef6\u8bef", "\u51b3\u7b56\u8d70\u5f2f", "\u91cd\u590d\u52b3\u52a8", "\u6210\u672c",
    "hours", "time", "cost", "productivity", "delay", "inefficient", "manual effort",
]

VALIDATION_OUTPUT = "data/processed/stage35_targeted_signal_validation.jsonl"


def _has(text: str, kws: list[str]) -> bool:
    lo = text.lower()
    return any(k.lower() in lo for k in kws)


def validate_stage35_signals(
    input_path: str | Path,
    output_path: str | Path = VALIDATION_OUTPUT,
    min_raw_text_chars: int = 80,
) -> list[dict]:
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        return []

    raw_rows: list[dict] = []
    with input_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_rows.append(dict(row))

    ids = next_ids("s35val", [], len(raw_rows))
    results: list[dict] = []

    for val_id, row in zip(ids, raw_rows):
        status = row.get("collection_status", "pending")
        if status != "collected":
            continue  # only validate collected rows

        errors: list[str] = []
        warnings: list[str] = []
        detected: list[str] = []

        raw_text = (row.get("raw_text") or "").strip()
        url = (row.get("url") or "").strip()
        source_note = (row.get("source_note") or "").strip()
        intent = row.get("evidence_intent", "")
        is_synthetic = str(row.get("is_synthetic", "false")).lower() in ("true", "1", "yes")
        exclude = str(row.get("exclude_from_truth_scoring", "false")).lower() in ("true", "1", "yes")
        group_id = (row.get("target_group_id") or "").strip()
        score_id = (row.get("target_truth_score_id") or "").strip()

        # Core checks
        if not group_id:
            errors.append("missing target_group_id")
        if not score_id:
            errors.append("missing target_truth_score_id")
        if not raw_text:
            errors.append("raw_text empty")
        elif len(raw_text) < min_raw_text_chars:
            errors.append(f"raw_text too short ({len(raw_text)} < {min_raw_text_chars} chars)")
        if not url and not source_note:
            errors.append("no source_url and no source_note")
        if is_synthetic:
            errors.append("is_synthetic must be false for Stage 3.5")
        if exclude:
            errors.append("exclude_from_truth_scoring must be false")

        combined = " ".join(filter(None, [raw_text, row.get("title", ""), source_note]))

        # Intent-specific keyword checks
        if intent in ("paid_alternative", "budget_signal"):
            if _has(combined, _PAY_KW):
                detected.append("payment_signal")
            else:
                warnings.append("paid intent: no payment/cost/subscription keywords found")
        elif intent in ("business_impact", "time_cost"):
            if _has(combined, _IMPACT_KW):
                detected.append("impact_signal")
            else:
                warnings.append("impact intent: no time/cost/productivity keywords found")
        elif intent in ("current_solution", "manual_workaround"):
            if _has(combined, _WA_KW):
                detected.append("workaround_signal")
            else:
                warnings.append("workaround intent: no manual/workaround/tool keywords found")

        if errors:
            v_status = "invalid"
            include = False
        elif warnings:
            v_status = "warning"
            include = True
        else:
            v_status = "valid"
            include = True

        results.append({
            "validation_id": val_id,
            "target_signal_id": row.get("target_signal_id", ""),
            "target_group_id": group_id,
            "evidence_intent": intent,
            "status": v_status,
            "validation_errors": errors,
            "validation_warnings": warnings,
            "detected_signal_types": detected,
            "include_in_combined_input": include,
            "raw_text_chars": len(raw_text),
            "created_at": utc_now_iso(),
        })

    output_path.write_text(
        "\n".join(__import__("json").dumps(r, ensure_ascii=False) for r in results) + "\n",
        encoding="utf-8",
    )
    return results


def load_stage35_validations(path: str | Path = VALIDATION_OUTPUT) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    results = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                results.append(__import__("json").loads(line))
            except Exception:
                pass
    return results
