"""Tests for Stage 3.4 evidence_attributor."""
import csv
import json
import pytest
from pathlib import Path
from datetime import datetime, timezone
from demand_radar.lineage.evidence_attributor import attribute_targeted_evidence


def _write_csv(path, rows, fieldnames):
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_jsonl(path, items):
    Path(path).write_text(
        "\n".join(json.dumps(i) for i in items) + "\n",
        encoding="utf-8"
    )


def _make_targeted_row(sig_id, url, status="collected", synthetic="False"):
    return {
        "target_signal_id": sig_id,
        "target_group_id": "grp_001",
        "target_group_title_zh": "测试候选",
        "target_truth_score_id": "ts_001",
        "evidence_intent": "paid_alternative",
        "collection_status": status,
        "is_synthetic": synthetic,
        "url": url,
        "raw_text": "Some content with price info.",
    }


COLS = ["target_signal_id", "target_group_id", "target_group_title_zh",
        "target_truth_score_id", "evidence_intent", "collection_status",
        "is_synthetic", "url", "raw_text"]


def test_attributed_to_expected_group(tmp_path):
    """Signal that traces all the way to expected group."""
    url = "https://example.com/pricing"
    raw_id = "sig_001"
    pp_id = "pp_001"
    cluster_id = "cluster_001"
    group_id = "grp_001"

    targeted = tmp_path / "targeted.csv"
    _write_csv(targeted, [_make_targeted_row("tsig_001", url)], COLS)

    raw = tmp_path / "raw.jsonl"
    _write_jsonl(raw, [{"raw_signal_id": raw_id, "url": url, "batch_id": "b1"}])

    pps = tmp_path / "pain_points.jsonl"
    _write_jsonl(pps, [{"pain_point_id": pp_id, "raw_signal_id": raw_id, "batch_id": "b1"}])

    clusters = tmp_path / "clusters.jsonl"
    _write_jsonl(clusters, [{"cluster_id": cluster_id, "related_pain_point_ids": [pp_id]}])

    groups = tmp_path / "groups.jsonl"
    _write_jsonl(groups, [{"group_id": group_id, "cluster_ids": [cluster_id]}])

    ts = tmp_path / "truth_scores.jsonl"
    _write_jsonl(ts, [{"truth_score_id": "ts_001", "source_group_id": group_id}])

    out = tmp_path / "attr.jsonl"
    results = attribute_targeted_evidence(
        targeted_path=targeted, raw_path=raw, pain_points_path=pps,
        clusters_path=clusters, reviewed_groups_path=groups,
        truth_scores_path=ts, output_path=out,
    )
    assert len(results) == 1
    assert results[0].attribution_status == "attributed_to_expected_group"
    assert results[0].attribution_confidence == pytest.approx(0.9)


def test_lost_in_extraction_no_raw(tmp_path):
    """Signal whose URL is not in raw_signals."""
    targeted = tmp_path / "targeted.csv"
    _write_csv(targeted, [_make_targeted_row("tsig_002", "https://notfound.com/x")], COLS)

    raw = tmp_path / "raw.jsonl"
    raw.write_text("", encoding="utf-8")
    pps = tmp_path / "pp.jsonl"; pps.write_text("", encoding="utf-8")
    clusters = tmp_path / "c.jsonl"; clusters.write_text("", encoding="utf-8")
    groups = tmp_path / "g.jsonl"; groups.write_text("", encoding="utf-8")
    ts = tmp_path / "ts.jsonl"; ts.write_text("", encoding="utf-8")
    out = tmp_path / "attr.jsonl"

    results = attribute_targeted_evidence(
        targeted_path=targeted, raw_path=raw, pain_points_path=pps,
        clusters_path=clusters, reviewed_groups_path=groups,
        truth_scores_path=ts, output_path=out,
    )
    assert len(results) == 1
    assert results[0].attribution_status == "lost_in_extraction"


def test_lost_in_extraction_no_pain_point(tmp_path):
    """Raw signal found but no pain_point generated."""
    url = "https://example.com/no-pain"
    raw_id = "sig_003"
    targeted = tmp_path / "t.csv"
    _write_csv(targeted, [_make_targeted_row("tsig_003", url)], COLS)
    raw = tmp_path / "raw.jsonl"
    _write_jsonl(raw, [{"raw_signal_id": raw_id, "url": url, "batch_id": "b1"}])
    pps = tmp_path / "pp.jsonl"; pps.write_text("", encoding="utf-8")
    clusters = tmp_path / "c.jsonl"; clusters.write_text("", encoding="utf-8")
    groups = tmp_path / "g.jsonl"; groups.write_text("", encoding="utf-8")
    ts = tmp_path / "ts.jsonl"; ts.write_text("", encoding="utf-8")
    out = tmp_path / "attr.jsonl"

    results = attribute_targeted_evidence(
        targeted_path=targeted, raw_path=raw, pain_points_path=pps,
        clusters_path=clusters, reviewed_groups_path=groups,
        truth_scores_path=ts, output_path=out,
    )
    assert results[0].attribution_status == "lost_in_extraction"
    assert results[0].raw_signal_id == raw_id


def test_lost_in_merge_no_group(tmp_path):
    """Signal gets to cluster but not to reviewed group."""
    url = "https://example.com/cluster-only"
    raw_id = "sig_004"
    pp_id = "pp_004"
    cluster_id = "cluster_004"

    targeted = tmp_path / "t.csv"
    _write_csv(targeted, [_make_targeted_row("tsig_004", url)], COLS)
    raw = tmp_path / "raw.jsonl"
    _write_jsonl(raw, [{"raw_signal_id": raw_id, "url": url, "batch_id": "b1"}])
    pps = tmp_path / "pp.jsonl"
    _write_jsonl(pps, [{"pain_point_id": pp_id, "raw_signal_id": raw_id, "batch_id": "b1"}])
    clusters = tmp_path / "c.jsonl"
    _write_jsonl(clusters, [{"cluster_id": cluster_id, "related_pain_point_ids": [pp_id]}])
    groups = tmp_path / "g.jsonl"; groups.write_text("", encoding="utf-8")
    ts = tmp_path / "ts.jsonl"; ts.write_text("", encoding="utf-8")
    out = tmp_path / "attr.jsonl"

    results = attribute_targeted_evidence(
        targeted_path=targeted, raw_path=raw, pain_points_path=pps,
        clusters_path=clusters, reviewed_groups_path=groups,
        truth_scores_path=ts, output_path=out,
    )
    assert results[0].attribution_status == "lost_in_merge"
    assert cluster_id in results[0].demand_cluster_ids
