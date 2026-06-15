"""Stage 3.4: Lineage propagation utilities."""
from __future__ import annotations
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def snapshot_truth_state(
    name: str,
    sources: dict[str, str] | None = None,
    base_dir: str | Path = "outputs/archive",
) -> Path:
    """Snapshot key processed files for lineage comparison."""
    now = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dest = Path(base_dir) / f"{name}_{now}" if not (Path(base_dir) / name).exists() else Path(base_dir) / name
    dest.mkdir(parents=True, exist_ok=True)

    if sources is None:
        sources = {
            "truth_scores.jsonl": "data/processed/truth_scores.jsonl",
            "calibrated_llm_ai_reviewed_cluster_groups.jsonl": (
                "data/processed/calibrated_llm_ai_reviewed_cluster_groups.jsonl"
            ),
            "evidence_gap_analysis.jsonl": "data/processed/evidence_gap_analysis.jsonl",
            "targeted_signal_collection_plan.jsonl": (
                "data/processed/targeted_signal_collection_plan.jsonl"
            ),
        }

    copied: list[str] = []
    for dest_name, src_path in sources.items():
        src = Path(src_path)
        if src.exists():
            shutil.copy2(src, dest / dest_name)
            copied.append(dest_name)

    # Write manifest
    manifest = {
        "name": name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "files": copied,
    }
    (dest / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    return dest


def load_snapshot_truth_scores(snapshot_dir: str | Path) -> list[dict]:
    """Load truth_scores from a snapshot directory."""
    path = Path(snapshot_dir) / "truth_scores.jsonl"
    if not path.exists():
        return []
    result = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                result.append(json.loads(line))
            except Exception:
                pass
    return result


def load_current_truth_scores(path: str | Path = "data/processed/truth_scores.jsonl") -> list[dict]:
    """Load current truth_scores.jsonl."""
    p = Path(path)
    if not p.exists():
        return []
    result = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                result.append(json.loads(line))
            except Exception:
                pass
    return result
