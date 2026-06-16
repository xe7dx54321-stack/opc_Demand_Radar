"""MVP-B: Store layer for domain relevance and pain items."""
from __future__ import annotations
import json
from pathlib import Path

from demand_radar.mvp_b.domain_relevance_schema import DomainRelevanceResult
from demand_radar.mvp_b.pain_extraction_schema import ExtractedPainItem

_RELEVANCE_PATH = Path("data/processed/mvp_b/domain_relevance_scores.jsonl")
_PAIN_PATH = Path("data/processed/mvp_b/extracted_pain_items.jsonl")


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


def _write_jsonl(path: Path, objs: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(o, ensure_ascii=False) for o in objs) + "\n",
        encoding="utf-8",
    )


def write_relevance_results(results: list[DomainRelevanceResult], path: Path | None = None) -> None:
    _write_jsonl(path or _RELEVANCE_PATH, [r.model_dump() for r in results])


def load_relevance_results(path: Path | None = None) -> list[DomainRelevanceResult]:
    return [DomainRelevanceResult(**d) for d in _load_jsonl(path or _RELEVANCE_PATH)]


def write_pain_items(items: list[ExtractedPainItem], path: Path | None = None) -> None:
    _write_jsonl(path or _PAIN_PATH, [it.model_dump() for it in items])


def load_pain_items(path: Path | None = None) -> list[ExtractedPainItem]:
    return [ExtractedPainItem(**d) for d in _load_jsonl(path or _PAIN_PATH)]


def load_relevance_dicts(path: Path | None = None) -> list[dict]:
    return _load_jsonl(path or _RELEVANCE_PATH)


def load_pain_dicts(path: Path | None = None) -> list[dict]:
    return _load_jsonl(path or _PAIN_PATH)