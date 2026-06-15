"""Tests for Stage 3.4 candidate_matcher."""
import pytest
from datetime import datetime, timezone
from demand_radar.lineage.candidate_matcher import match_candidate_lineage, _title_similarity
from demand_radar.lineage.lineage_schema import TargetedEvidenceAttribution

NOW = datetime.now(timezone.utc).isoformat()


def _score(gid, title, score=65.0, level="medium", personas=None, domains=None):
    return {
        "truth_score_id": f"ts_{gid}",
        "source_group_id": gid,
        "group_title_zh": title,
        "truth_score": score,
        "truth_level": level,
        "recommended_next_action": "needs_more_evidence",
        "personas": personas or [],
        "domain_tags": domains or [],
    }


def _attr(sig_id, target_gid, reviewed_gids=None, status="attributed_to_expected_group"):
    return TargetedEvidenceAttribution(
        attribution_id=f"attr_{sig_id}",
        target_signal_id=sig_id,
        target_group_id=target_gid,
        attribution_status=status,
        attribution_confidence=0.9 if reviewed_gids else 0.3,
        attribution_reason_zh="test",
        reviewed_group_ids=reviewed_gids or [],
        created_at=NOW,
    )


def test_title_similarity_chinese():
    a = "\u6295\u8d44\u4ebaAI\u4ea7\u4e1a\u8ddf\u8e2a\u4fe1\u606f\u5206\u6563"
    b = "\u6295\u8d44\u4ebaAI\u4ea7\u4e1a\u8ddf\u8e2a\u4fe1\u606f\u5206\u6563\u95ee\u9898"
    sim = _title_similarity(a, b)
    assert sim > 0.5


def test_title_similarity_different():
    sim = _title_similarity("\u5185\u5bb9\u56e2\u961f\u9009\u9898", "\u6295\u8d44\u4ebaAI")
    assert sim < 0.5


def test_group_id_match_gives_weak_lineage(tmp_path):
    before = [_score("grp_001", "\u6295\u8d44\u4ebaAI\u4ea7\u4e1a\u8ddf\u8e2a", score=51.4, level="weak")]
    after = [_score("grp_001", "\u6295\u8d44\u4ebaAI\u4ea7\u4e1a\u8ddf\u8e2a\u4fe1\u606f\u6574\u7406\u4f4e\u6548", score=66.4)]
    lineages = match_candidate_lineage(before, after, [], output_path=str(tmp_path / "l.jsonl"))
    assert len(lineages) >= 1
    matched = [l for l in lineages if l.before_group_id == "grp_001" and l.after_group_id == "grp_001"]
    assert len(matched) == 1
    assert matched[0].match_strength in ("strong", "weak")


def test_targeted_signal_overlap_improves_score(tmp_path):
    before = [_score("grp_B", "\u4f01\u4e1a\u77e5\u8bc6\u5de5\u4f5c\u6d41\u68c0\u7d22\u56f0\u96be")]
    after = [_score("grp_A", "\u4f01\u4e1a\u77e5\u8bc6\u5de5\u4f5c\u6d41\u68c0\u7d22\u56f0\u96be\u89e3\u51b3")]
    attrs_with = [_attr("tsig_001", "grp_B", reviewed_gids=["grp_A"])]
    lw = match_candidate_lineage(before, after, attrs_with, output_path=str(tmp_path / "l1.jsonl"))
    lwo = match_candidate_lineage(before, after, [], output_path=str(tmp_path / "l2.jsonl"))
    sw = next((l.match_score for l in lw if l.before_group_id == "grp_B"), 0)
    swo = next((l.match_score for l in lwo if l.before_group_id == "grp_B"), 0)
    assert sw >= swo


def test_unmatched_before_when_no_after(tmp_path):
    before = [_score("grp_X", "\u67d0\u65e7\u5019\u9009\u65e0\u5bf9\u5e94")]
    after = [_score("grp_Y", "\u5b8c\u5168\u4e0d\u76f8\u5173\u5185\u5bb9")]
    lineages = match_candidate_lineage(before, after, [], output_path=str(tmp_path / "l.jsonl"))
    matched = [l for l in lineages if l.before_group_id == "grp_X"]
    assert len(matched) == 1
    assert matched[0].match_score < 0.55


def test_missing_baseline_for_new_after(tmp_path):
    before = [_score("grp_001", "\u5df2\u6709\u5019\u9009")]
    after = [_score("grp_001", "\u5df2\u6709\u5019\u9009"), _score("grp_new", "\u5168\u65b0\u5019\u9009")]
    lineages = match_candidate_lineage(before, after, [], output_path=str(tmp_path / "l.jsonl"))
    new_ones = [l for l in lineages if l.match_strength == "missing_baseline"]
    assert len(new_ones) >= 1
    assert new_ones[0].after_group_id == "grp_new"


def test_merged_candidate_detected(tmp_path):
    """Two before candidates both mapping to same after via targeted-signal overlap."""
    # grp_A and grp_B (befores) each have targeted signals that arrived in grp_C (after).
    # Targeted-signal overlap (weight 0.35) + persona+domain (0.25) crosses the 0.50 threshold
    # for BOTH befores, making matched_before["grp_C"] have 2 entries -> merged flag.
    before = [
        _score("grp_A", "\u5185\u5bb9\u56e2\u961f\u9009\u9898\u4fe1\u606f\u5206\u6563",
               personas=["\u5185\u5bb9\u8fd0\u8425"], domains=["content"]),
        _score("grp_B", "\u5185\u5bb9\u56e2\u961f\u9009\u9898\u4eba\u5de5\u6574\u7406\u4f4e\u6548",
               personas=["\u5185\u5bb9\u8fd0\u8425"], domains=["content"]),
    ]
    after = [
        _score("grp_C", "\u5185\u5bb9\u56e2\u961f\u9009\u9898\u4fe1\u606f\u5206\u6563\u4e0e\u4eba\u5de5\u6574\u7406\u4f4e\u6548",
               personas=["\u5185\u5bb9\u8fd0\u8425"], domains=["content"]),
    ]
    # Targeted signals: one from grp_A and one from grp_B both arrived in grp_C
    attrs = [
        _attr("tsig_A1", "grp_A", reviewed_gids=["grp_C"]),
        _attr("tsig_B1", "grp_B", reviewed_gids=["grp_C"]),
    ]
    lineages = match_candidate_lineage(before, after, attrs, output_path=str(tmp_path / "l.jsonl"))
    before_lineages = [l for l in lineages if l.before_group_id in ("grp_A", "grp_B")]
    assert len(before_lineages) >= 2, f"Got lineages: {[(l.before_group_id, l.match_strength, l.match_score) for l in lineages]}"
    merged = [l for l in lineages if l.match_strength == "merged"]
    assert len(merged) >= 1, f"Expected merged; got: {[(l.before_group_id, l.match_strength, round(l.match_score,3)) for l in lineages]}"


def test_output_written(tmp_path):
    before = [_score("grp_001", "\u6d4b\u8bd5\u5019\u9009")]
    after = [_score("grp_001", "\u6d4b\u8bd5\u5019\u9009\u6269\u5c55")]
    out = tmp_path / "lineage.jsonl"
    match_candidate_lineage(before, after, [], output_path=str(out))
    assert out.exists()
    assert out.stat().st_size > 0
