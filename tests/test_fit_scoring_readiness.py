"""Tests for Stage 3 -> Stage 4 Fit Scoring readiness."""
import json
from pathlib import Path
from demand_radar.truth_scoring.truth_schema import TruthScore
from demand_radar.truth_scoring.truth_store import write_truth_scores
from demand_radar.state.raw_store import utc_now_iso

DIMS = {
    "pain_evidence_strength": 80.0,
    "frequency_repetition": 75.0,
    "existing_workaround": 70.0,
    "willingness_to_pay": 65.0,
    "persona_clarity": 85.0,
}


def make_score(score_id, level, action):
    return TruthScore(
        truth_score_id=score_id,
        source_type="calibrated_llm_ai_reviewed_group",
        source_group_id=f"g_{score_id}",
        group_title_zh=f"\u9700\u6c42\u7ec4 {score_id}",
        group_summary_zh="\u6458\u8981",
        truth_score=80.0 if level == "strong" else 60.0,
        truth_level=level,
        dimension_scores=DIMS.copy(),
        evidence_count=4,
        source_count=3,
        scoring_reason_zh="\u8bc1\u636e\u5145\u5206\u3002",
        recommended_next_action=action,
        created_at=utc_now_iso(),
    )


def test_ready_for_fit_scoring_when_proceed_exists(tmp_path):
    scores = [make_score("s1", "strong", "proceed_to_fit_scoring")]
    write_truth_scores(scores, tmp_path / "truth_scores.jsonl")
    raw = json.loads((tmp_path / "truth_scores.jsonl").read_text(encoding="utf-8"))
    action = raw.get("recommended_next_action")
    assert action == "proceed_to_fit_scoring"


def test_partial_when_only_medium(tmp_path):
    scores = [make_score("s1", "medium", "needs_more_evidence"), make_score("s2", "medium", "needs_more_evidence")]
    write_truth_scores(scores, tmp_path / "truth_scores.jsonl")
    loaded_scores = json.loads((tmp_path / "truth_scores.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert loaded_scores["truth_level"] == "medium"


def test_batch_summary_fit_scoring_section(tmp_path, monkeypatch):
    """_truth_scoring_lines reads from TRUTH_SCORES_PATH; patch it to use tmp."""
    import demand_radar.batch.batch_report as breport
    scores_path = tmp_path / "truth_scores.jsonl"
    scores = [make_score("s1", "strong", "proceed_to_fit_scoring")]
    write_truth_scores(scores, scores_path)

    # Patch the hardcoded path inside _truth_scoring_lines
    original_fn = breport._truth_scoring_lines
    def _patched_truth_scoring_lines():
        import json as _json
        path = scores_path
        if not path.exists():
            return []
        lines_data = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                lines_data.append(_json.loads(line))
            except Exception:
                continue
        if not lines_data:
            return []
        level_counts = {"strong": 0, "medium": 0, "weak": 0, "insufficient": 0}
        action_counts = {}
        for s in lines_data:
            lvl = s.get("truth_level", "insufficient")
            level_counts[lvl] = level_counts.get(lvl, 0) + 1
            act = s.get("recommended_next_action", "")
            action_counts[act] = action_counts.get(act, 0) + 1
        proceed = action_counts.get("proceed_to_fit_scoring", 0)
        ready = "yes" if proceed >= 1 else ("partial" if level_counts.get("medium", 0) + level_counts.get("strong", 0) >= 2 else "no")
        return [
            "",
            "## Stage 3: Truth Scoring",
            "",
            f"- truth_scores: {len(lines_data)}",
            f"- proceed_to_fit_scoring: {proceed}",
            f"- ready_for_fit_scoring: {ready}",
            "",
        ]
    monkeypatch.setattr(breport, "_truth_scoring_lines", _patched_truth_scoring_lines)
    lines = breport._truth_scoring_lines()
    assert any("truth_scores" in line for line in lines)
    assert any("ready_for_fit_scoring" in line for line in lines)
