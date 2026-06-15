"""Stage 3.5 candidate selector."""
from __future__ import annotations
import json
from pathlib import Path
from demand_radar.stage35.stage35_schema import Stage35SelectedCandidate
from demand_radar.stage35.stage35_store import write_selected_candidates
from demand_radar.state.raw_store import next_ids, utc_now_iso

_PREFERRED = [
    "AI\u4ea7\u4e1a\u8ddf\u8e2a",
    "\u9879\u76ee\u521d\u7b5b",
    "\u4f01\u4e1a\u77e5\u8bc6",
    "\u77e5\u8bc6\u5de5\u4f5c\u6d41",
]
_EXCLUDE = [
    "\u5185\u5bb9\u56e2\u961f\u9009\u9898",
    "AI Agent\u5de5\u4f5c\u6d41",
]

_PRIORITY_INTENTS = [
    "paid_alternative",
    "budget_signal",
    "current_solution",
    "business_impact",
    "time_cost",
    "manual_workaround",
]


def _matches_preferred(title: str) -> bool:
    return any(kw in title for kw in _PREFERRED)


def _matches_exclude(title: str) -> bool:
    return any(kw in title for kw in _EXCLUDE)


def select_stage35_candidates(
    truth_scores_path: str | Path = "data/processed/truth_scores.jsonl",
    max_candidates: int = 2,
    signals_per_candidate: int = 12,
    output_path: str | Path = "data/processed/stage35_selected_candidates.jsonl",
) -> list[Stage35SelectedCandidate]:
    truth_scores_path = Path(truth_scores_path)
    scores: list[dict] = []
    if truth_scores_path.exists():
        for line in truth_scores_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    scores.append(json.loads(line))
                except Exception:
                    pass

    # Filter by preferred/exclude keywords
    eligible = []
    for s in scores:
        title = s.get("group_title_zh", "")
        if _matches_exclude(title):
            continue
        if _matches_preferred(title):
            eligible.append((True, s))
        else:
            eligible.append((False, s))

    # Sort: preferred first, then by truth_score descending
    eligible.sort(key=lambda x: (not x[0], -(x[1].get("truth_score") or 0)))

    selected_scores = [s for _, s in eligible[:max_candidates]]

    ids = next_ids("s35cand", [], len(selected_scores))
    candidates = []
    for rank, (cand_id, sc) in enumerate(zip(ids, selected_scores), start=1):
        title = sc.get("group_title_zh", "")
        if _matches_preferred(title):
            reason = f"\u5339\u914d\u80fd\u529b\u5708\u5173\u952e\u8bcd\uff0c\u8bc1\u636e\u7f3a\u53e3\u9700\u8981\u8865\u5145\uff1a{title[:30]}"
        else:
            reason = f"\u5f53\u524d\u5f97\u5206\u6700\u9ad8\uff0c\u4f18\u5148\u538b\u5f3a\u9a8c\u8bc1\uff1a{title[:30]}"
        candidates.append(Stage35SelectedCandidate(
            selected_candidate_id=cand_id,
            truth_score_id=sc.get("truth_score_id", ""),
            source_group_id=sc.get("source_group_id", ""),
            group_title_zh=title,
            current_truth_score=float(sc.get("truth_score") or 0),
            current_truth_level=sc.get("truth_level", ""),
            current_next_action=sc.get("recommended_next_action", ""),
            selected_reason_zh=reason,
            priority_rank=rank,
            target_new_signals=signals_per_candidate,
            target_evidence_intents=_PRIORITY_INTENTS[:],
            created_at=utc_now_iso(),
        ))

    write_selected_candidates(candidates, path=str(output_path))
    return candidates
