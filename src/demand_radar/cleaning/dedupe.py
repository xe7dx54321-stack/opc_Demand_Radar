"""Lightweight dedupe helpers."""

from __future__ import annotations

from difflib import SequenceMatcher


def similarity(left: str, right: str) -> float:
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left.lower().strip(), right.lower().strip()).ratio()


def is_near_duplicate(left: str, right: str, threshold: float = 0.92) -> bool:
    return similarity(left, right) >= threshold

