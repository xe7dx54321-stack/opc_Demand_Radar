"""Input loader for Truth Scoring (Stage 3).

Reads reviewed cluster groups with fallback priority:
1. calibrated_llm_ai_reviewed_cluster_groups.jsonl
2. llm_ai_reviewed_cluster_groups.jsonl
3. ai_reviewed_cluster_groups.jsonl
4. reviewed_cluster_groups.jsonl
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CALIBRATED_LLM_PATH = Path("data/processed/calibrated_llm_ai_reviewed_cluster_groups.jsonl")
LLM_PATH = Path("data/processed/llm_ai_reviewed_cluster_groups.jsonl")
AI_PATH = Path("data/processed/ai_reviewed_cluster_groups.jsonl")
HUMAN_PATH = Path("data/processed/reviewed_cluster_groups.jsonl")

SOURCE_PATHS: dict[str, Path] = {
    "calibrated_llm": CALIBRATED_LLM_PATH,
    "llm": LLM_PATH,
    "ai": AI_PATH,
    "human": HUMAN_PATH,
}

PRIORITY_ORDER = ["calibrated_llm", "llm", "ai", "human"]


def load_reviewed_groups(
    source: str = "auto",
) -> list[dict[str, Any]]:
    """Load reviewed groups for truth scoring.

    Args:
        source: One of 'auto', 'calibrated_llm', 'llm', 'ai', 'human', 'combined'.
                'auto' picks the highest-priority source that exists.
                'combined' loads all available sources without duplicates.
    Returns:
        List of group dicts, each with a '_source_type' key injected.
    """
    if source == "auto":
        for src_name in PRIORITY_ORDER:
            path = SOURCE_PATHS[src_name]
            if path.exists():
                groups = _load_jsonl(path, src_name)
                if groups:
                    return groups
        return []

    if source == "combined":
        seen_ids: set[str] = set()
        all_groups: list[dict[str, Any]] = []
        for src_name in PRIORITY_ORDER:
            path = SOURCE_PATHS.get(src_name)
            if path and path.exists():
                for g in _load_jsonl(path, src_name):
                    gid = g.get("group_id", "")
                    if gid not in seen_ids:
                        seen_ids.add(gid)
                        all_groups.append(g)
        return all_groups

    path = SOURCE_PATHS.get(source)
    if path is None:
        raise ValueError(f"Unknown source: {source!r}. Choose from {list(SOURCE_PATHS)}")
    if not path.exists():
        return []
    return _load_jsonl(path, source)


def _load_jsonl(path: Path, source_type: str) -> list[dict[str, Any]]:
    groups = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            g = json.loads(line)
            g["_source_type"] = source_type
            groups.append(g)
        except json.JSONDecodeError:
            continue
    return groups


def resolve_source_type_label(source_type: str) -> str:
    labels = {
        "calibrated_llm": "calibrated_llm_ai_reviewed_group",
        "llm": "llm_ai_reviewed_group",
        "ai": "ai_reviewed_group",
        "human": "human_reviewed_group",
    }
    return labels.get(source_type, source_type)
