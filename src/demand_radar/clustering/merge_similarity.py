"""Similarity diagnostics for Stage 2.5 cluster merge suggestions."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Iterable

from demand_radar.clustering.cluster_schema import DemandCluster


DEFAULT_MERGE_WEIGHTS = {
    "title_weight": 0.20,
    "summary_weight": 0.25,
    "pain_description_weight": 0.25,
    "workaround_weight": 0.10,
    "persona_weight": 0.10,
    "domain_weight": 0.10,
}

CHINESE_SIGNAL_PHRASES = [
    "信息分散",
    "人工整理",
    "人工整理低效",
    "容易遗漏",
    "难验证",
    "验证困难",
    "噪音过多",
    "检索困难",
    "总结困难",
    "耗时过多",
    "文档不完整",
    "流程不可靠",
    "替代方案",
    "付费数据库",
    "人工搜索",
    "人工表格",
    "内容选题",
    "产业跟踪",
    "开发者工具链",
    "智能体工作流",
    "知识工作流",
]

STOPWORDS = {
    "问题",
    "需求",
    "相关",
    "工作",
    "工作流",
    "用户",
    "候选",
    "进一步",
    "人工",
    "复核",
    "需要",
    "当前",
    "出现",
    "反复",
    "共有",
    "痛点",
    "证据",
    "主题",
    "the",
    "and",
    "for",
    "with",
    "from",
}


@dataclass(frozen=True)
class MergeSimilarityResult:
    field_scores: dict[str, float]
    shared_personas: list[str] = field(default_factory=list)
    shared_domain_tags: list[str] = field(default_factory=list)
    shared_keywords: list[str] = field(default_factory=list)
    total: float = 0.0


def cluster_merge_similarity(
    left: DemandCluster,
    right: DemandCluster,
    weights: dict[str, float] | None = None,
) -> MergeSimilarityResult:
    active_weights = {**DEFAULT_MERGE_WEIGHTS, **(weights or {})}
    field_scores = {
        "title_similarity": text_similarity(left.cluster_title_zh, right.cluster_title_zh),
        "summary_similarity": text_similarity(left.cluster_summary_zh, right.cluster_summary_zh),
        "pain_description_similarity": list_text_similarity(
            left.representative_pain_descriptions,
            right.representative_pain_descriptions,
        ),
        "workaround_similarity": list_text_similarity(left.current_workarounds, right.current_workarounds),
        "persona_similarity": overlap_similarity(set(left.personas), set(right.personas)),
        "domain_similarity": overlap_similarity(set(left.domain_tags), set(right.domain_tags)),
    }
    total = (
        field_scores["title_similarity"] * active_weights["title_weight"]
        + field_scores["summary_similarity"] * active_weights["summary_weight"]
        + field_scores["pain_description_similarity"] * active_weights["pain_description_weight"]
        + field_scores["workaround_similarity"] * active_weights["workaround_weight"]
        + field_scores["persona_similarity"] * active_weights["persona_weight"]
        + field_scores["domain_similarity"] * active_weights["domain_weight"]
    )
    return MergeSimilarityResult(
        field_scores={key: round(value, 2) for key, value in field_scores.items()},
        shared_personas=_shared_list(left.personas, right.personas),
        shared_domain_tags=_shared_list(left.domain_tags, right.domain_tags),
        shared_keywords=shared_keywords(left, right),
        total=round(total, 2),
    )


def text_similarity(left: str, right: str) -> float:
    left_norm = _normalize_text(left)
    right_norm = _normalize_text(right)
    if not left_norm or not right_norm:
        return 0.0
    sequence = SequenceMatcher(None, left_norm, right_norm).ratio() * 100
    tokens = overlap_similarity(set(_tokens(left_norm)), set(_tokens(right_norm)))
    phrase = overlap_similarity(set(_signal_phrases(left)), set(_signal_phrases(right)))
    return round(max(sequence, tokens, phrase), 2)


def list_text_similarity(left: Iterable[str], right: Iterable[str]) -> float:
    left_text = " ".join(item for item in left if item)
    right_text = " ".join(item for item in right if item)
    return text_similarity(left_text, right_text)


def overlap_similarity(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    union = left | right
    if not union:
        return 0.0
    return round(100.0 * len(left & right) / len(union), 2)


def shared_keywords(left: DemandCluster, right: DemandCluster, max_keywords: int = 10) -> list[str]:
    left_keywords = _keyword_set(_cluster_text(left))
    right_keywords = _keyword_set(_cluster_text(right))
    shared = sorted(left_keywords & right_keywords, key=lambda value: (-len(value), value))
    return shared[:max_keywords]


def _cluster_text(cluster: DemandCluster) -> str:
    return " ".join(
        [
            cluster.cluster_title_zh,
            cluster.cluster_summary_zh,
            *cluster.representative_pain_descriptions,
            *cluster.current_workarounds,
        ]
    )


def _keyword_set(text: str) -> set[str]:
    keywords = set(_signal_phrases(text))
    keywords.update(
        token
        for token in _tokens(_normalize_text(text))
        if _is_ascii_keyword(token) and token not in STOPWORDS and len(token) >= 2
    )
    return keywords


def _signal_phrases(text: str) -> list[str]:
    return [phrase for phrase in CHINESE_SIGNAL_PHRASES if phrase in text]


def _tokens(text: str) -> list[str]:
    return [token for token in text.split() if token and token not in STOPWORDS]


def _normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[_\-/]+", " ", text)
    text = re.sub(r"[^\w\u4e00-\u9fff]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _is_ascii_keyword(token: str) -> bool:
    return token.isascii() and any(char.isalpha() for char in token)


def _shared_list(left: list[str], right: list[str]) -> list[str]:
    right_set = set(right)
    return [item for item in left if item in right_set]
