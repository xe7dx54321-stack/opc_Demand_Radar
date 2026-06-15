"""Stage 3.5 targeted signal template builder."""
from __future__ import annotations
import csv
import json
from pathlib import Path
from demand_radar.state.raw_store import utc_now_iso

_PAYMENT_INTENTS = {"paid_alternative", "budget_signal"}
_WORKAROUND_INTENTS = {"manual_workaround", "current_solution"}
_IMPACT_INTENTS = {"business_impact", "time_cost"}

_SOURCE_BY_INTENT = {
    "paid_alternative": "pricing_page",
    "budget_signal": "product_review",
    "manual_workaround": "forum_post",
    "current_solution": "community_discussion",
    "business_impact": "case_study",
    "time_cost": "forum_post",
    "product_review": "product_review",
    "case_study": "case_study",
    "pricing_page": "pricing_page",
    "landing_page": "landing_page",
}

_STAGE35_KW: dict[str, list[str]] = {
    "paid_alternative": [
        "AI\u4ea7\u4e1a\u8ddf\u8e2a\u5de5\u5177 \u4ed8\u8d39 \u8ba2\u9605",
        "\u6295\u8d44\u7814\u7a76 SaaS \u4ef7\u683c",
        "\u4f01\u4e1a\u77e5\u8bc6\u5e93 \u9879\u76ee\u7ba1\u7406 \u4e91 \u4ed8\u8d39",
        "knowledge management tool pricing enterprise",
        "AI market intelligence subscription cost",
    ],
    "budget_signal": [
        "\u6295\u7814\u5de5\u5177 \u9884\u7b97 \u5e74\u8d39 \u5e94\u7528",
        "\u4f01\u4e1a\u77e5\u8bc6 \u91c7\u8d2d \u8f6f\u4ef6 \u8bc4\u4f30",
        "investment research software budget team",
        "enterprise search procurement cost",
    ],
    "current_solution": [
        "\u6295\u8d44\u4eba \u73b0\u5728\u7528 \u624b\u52a8\u6574\u7406 \u4fe1\u606f\u6765\u6e90",
        "\u5f53\u524d\u5de5\u5177\u94fe \u77e5\u8bc6\u68c0\u7d22 \u5185\u90e8\u7cfb\u7edf",
        "current workflow knowledge retrieval internal tool",
        "investor research current process information gathering",
    ],
    "manual_workaround": [
        "\u4eba\u5de5\u6574\u7406 \u591a\u4e2a\u5de5\u5177 \u4fe1\u606f\u5206\u6563",
        "\u8868\u683c\u8bb0\u5f55 \u624b\u52a8\u66f4\u65b0 AI\u9879\u76ee",
        "manual data aggregation research analyst spreadsheet",
        "knowledge worker information overload manual process",
    ],
    "business_impact": [
        "\u4fe1\u606f\u5206\u6563 \u4e1a\u52a1\u5f71\u54cd \u51b3\u7b56\u5ef6\u8bef",
        "\u4f01\u4e1a\u77e5\u8bc6\u6562\u5931 \u4eba\u529b\u6210\u672c \u5de5\u4f5c\u6548\u7387",
        "business impact missed deals slow research",
        "knowledge gap cost analyst productivity lost",
    ],
    "time_cost": [
        "\u6bcf\u5468\u4eba\u5de5\u6d4f\u89c8 \u65f6\u95f4\u6d6a\u8d39 \u4e1a\u52a1\u6570\u636e",
        "\u6bcf\u5929\u641c\u96c6\u4fe1\u606f \u91cd\u590d\u52b3\u52a8 \u7814\u7a76\u5458",
        "hours spent manually gathering AI news",
        "time cost information research enterprise analyst",
    ],
}

TEMPLATE_COLS = [
    "target_signal_id", "target_group_id", "target_group_title_zh",
    "target_truth_score_id", "target_current_score", "target_gap_types",
    "evidence_intent", "desired_source_type", "desired_language",
    "suggested_keywords", "title", "raw_text", "url", "source_name",
    "source_type", "published_at", "language", "domain_tags",
    "batch_id", "source_note", "signal_focus", "expected_quality",
    "is_synthetic", "exclude_from_truth_scoring",
    "collection_status", "collector_note",
    "stage35_candidate_priority", "stage35_required_signal_type",
    "stage35_quality_bar", "stage35_collection_hint_zh",
]


def _allocate_intents(n: int) -> list[str]:
    """Allocate intents per Stage 3.5 ratio requirements.

    payment_or_cost (paid_alternative / budget_signal / business_impact / time_cost)
        must be >= 60% of total rows.
    workaround/current_solution (current_solution / manual_workaround)
        must be >= 25%.
    """
    import math
    # workaround bucket: ceil to guarantee >= 25% for any n
    wa_n = math.ceil(n * 0.25)
    # payment_or_cost bucket: fills the rest, always >= 60%
    pay_n = n - wa_n
    other_n = 0

    # payment/cost pool includes business_impact and time_cost per spec
    pay_pool = ["paid_alternative", "budget_signal", "business_impact", "time_cost"]
    wa_pool = ["current_solution", "manual_workaround"]

    intents: list[str] = []
    for i in range(pay_n):
        intents.append(pay_pool[i % len(pay_pool)])
    for i in range(wa_n):
        intents.append(wa_pool[i % len(wa_pool)])
    # fill remainder with more payment intents
    for i in range(max(0, other_n)):
        intents.append(pay_pool[i % len(pay_pool)])
    return intents[:n]


def build_stage35_template(
    selected_candidates_path: str | Path = "data/processed/stage35_selected_candidates.jsonl",
    output_path: str | Path = "examples/stage35_targeted_signal_template.csv",
    total_rows: int = 24,
) -> list[dict]:
    from demand_radar.stage35.stage35_schema import Stage35SelectedCandidate
    sel_path = Path(selected_candidates_path)
    candidates: list[Stage35SelectedCandidate] = []
    if sel_path.exists():
        for line in sel_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    candidates.append(Stage35SelectedCandidate.model_validate_json(line))
                except Exception:
                    pass

    if not candidates:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=TEMPLATE_COLS, extrasaction="ignore")
            w.writeheader()
        return []

    rows_per = max(total_rows // len(candidates), 10)
    rows: list[dict] = []
    counter = 1

    for rank, cand in enumerate(candidates, start=1):
        n = rows_per if rank < len(candidates) else (total_rows - len(rows))
        n = max(n, 10)
        intents = _allocate_intents(n)
        for i, intent in enumerate(intents):
            sig_id = f"s35_{cand.source_group_id[:8]}_{counter:03d}"
            counter += 1
            kws = _STAGE35_KW.get(intent, [""])
            kw_str = " | ".join(kws[:3])
            hint = (
                f"\u9488\u5bf9\u300c{cand.group_title_zh[:20]}\u300d\uff0c"
                f"\u8865\u5145{intent}\u7c7b\u578b\u8bc1\u636e"
            )
            source_type = _SOURCE_BY_INTENT.get(intent, "forum_post")
            row = {
                "target_signal_id": sig_id,
                "target_group_id": cand.source_group_id,
                "target_group_title_zh": cand.group_title_zh,
                "target_truth_score_id": cand.truth_score_id,
                "target_current_score": cand.current_truth_score,
                "target_gap_types": "paid_alternative|budget_signal|manual_workaround",
                "evidence_intent": intent,
                "desired_source_type": source_type,
                "desired_language": "zh|en",
                "suggested_keywords": kw_str,
                "title": "",
                "raw_text": "",
                "url": "",
                "source_name": "",
                "source_type": source_type,
                "published_at": "",
                "language": "",
                "domain_tags": "",
                "batch_id": "batch_stage35_targeted",
                "source_note": "",
                "signal_focus": intent,
                "expected_quality": "high",
                "is_synthetic": "false",
                "exclude_from_truth_scoring": "false",
                "collection_status": "pending",
                "collector_note": "",
                "stage35_candidate_priority": rank,
                "stage35_required_signal_type": intent,
                "stage35_quality_bar": "\u5fc5\u987b\u5305\u542b\u5177\u4f53\u4ef7\u683c/\u6210\u672c/\u66ff\u4ee3\u65b9\u6848\u4fe1\u606f",
                "stage35_collection_hint_zh": hint,
            }
            rows.append(row)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=TEMPLATE_COLS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return rows
