"""MVP-B: Pain extraction runner with caching and retry."""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml

from demand_radar.mvp_b.pain_extraction_schema import ExtractedPainItem
from demand_radar.state.raw_store import next_ids, utc_now_iso

_CONFIG_PATH = Path("configs/pain_extraction_config.yaml")
_CACHE_DIR = Path(".llm_cache/mvp_b")


def _load_config(config_path: Path | None = None) -> dict[str, Any]:
    p = config_path or _CONFIG_PATH
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f).get("pain_extraction", {})


def _reject_item(
    pain_item_id: str,
    candidate_id: str,
    reject_reason: str,
    source_url: str | None = None,
    source_type: str | None = None,
    title: str | None = None,
    model: str | None = None,
) -> ExtractedPainItem:
    return ExtractedPainItem(
        pain_item_id=pain_item_id,
        candidate_id=candidate_id,
        should_extract=False,
        reject_reason=reject_reason,
        evidence_strength="reject",
        confidence=0.0,
        source_url=source_url,
        source_type=source_type,
        title=title,
        model=model,
        created_at=utc_now_iso(),
    )


def _build_extraction_prompt(
    candidate: dict,
    relevance: dict | None,
    max_chars: int = 6000,
) -> tuple[str, str]:
    cid = candidate.get("candidate_id", "")
    title = candidate.get("title") or "(no title)"
    source_type = candidate.get("source_type", "")
    source_url = candidate.get("source_url", "")
    raw_text = (candidate.get("raw_text") or "")[:max_chars]
    signals = str(candidate.get("detected_signal_types", []))

    rel_decision = "unknown"
    rel_score = 0.0
    if relevance:
        rel_decision = relevance.get("relevance_decision", "unknown")
        rel_score = relevance.get("relevance_score", 0.0)

    system = (
        "You are a demand signal extraction specialist for investment research and AI-assisted analysis workflows. "
        "Extract structured pain point information. Output ONLY valid JSON."
    )
    user = (
        f"Extract pain signals from this investment-domain evidence:\n\n"
        f"Title: {title}\nSource: {source_type} | {source_url}\n"
        f"Domain relevance: {rel_decision} (score: {rel_score:.2f})\n"
        f"Detected signal types: {signals}\n\n"
        f"Raw text (truncated to {max_chars} chars):\n{raw_text}\n\n"
        f'Output JSON:\n{{"candidate_id": "{cid}", "should_extract": true, "reject_reason": null, '
        f'"persona": null, "persona_confidence": 0.0, "workflow_stage": null, "job_to_be_done": null, '
        f'"pain_type": null, "pain_description_zh": null, "evidence_quote": null, '
        f'"current_solution": null, "paid_alternative": null, "business_impact": null, '
        f'"time_cost_signal": null, "budget_signal": null, "commercial_signal_type": null, '
        f'"evidence_strength": "medium", "confidence": 0.0, "reasoning_summary_zh": null}}'
    )
    return system, user


def _parse_extraction_response(raw: str) -> dict[str, Any]:
    text = raw.strip()
    text = re.sub(r"```(?:json)?\s*", "", text).replace("```", "")
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start:end + 1]
    return json.loads(text)


def _build_pain_item_from_data(
    pain_item_id: str,
    candidate: dict,
    data: dict[str, Any],
    model: str | None = None,
    prompt_version: str = "pain_extraction_v1",
) -> ExtractedPainItem:
    should_extract = bool(data.get("should_extract", False))
    evidence_strength = str(data.get("evidence_strength") or "weak")
    confidence = float(data.get("confidence") or 0.0)
    confidence = max(0.0, min(1.0, confidence))
    evidence_quote = data.get("evidence_quote") or None
    reject_reason = data.get("reject_reason") or None

    # Enforce: should_extract=True needs evidence_quote
    if should_extract and not evidence_quote:
        should_extract = False
        reject_reason = "evidence_quote missing in LLM output"
        evidence_strength = "reject"

    # Enforce: should_extract=False needs reject_reason
    if not should_extract and not reject_reason:
        reject_reason = "LLM returned should_extract=false without reason"

    return ExtractedPainItem(
        pain_item_id=pain_item_id,
        candidate_id=candidate.get("candidate_id", ""),
        should_extract=should_extract,
        reject_reason=reject_reason,
        persona=data.get("persona"),
        persona_confidence=float(data.get("persona_confidence") or 0.0) if data.get("persona_confidence") is not None else None,
        workflow_stage=data.get("workflow_stage"),
        job_to_be_done=data.get("job_to_be_done"),
        pain_type=data.get("pain_type"),
        pain_description_zh=data.get("pain_description_zh"),
        evidence_quote=evidence_quote,
        current_solution=data.get("current_solution"),
        paid_alternative=data.get("paid_alternative"),
        business_impact=data.get("business_impact"),
        time_cost_signal=data.get("time_cost_signal"),
        budget_signal=data.get("budget_signal"),
        commercial_signal_type=data.get("commercial_signal_type"),
        evidence_strength=evidence_strength,
        confidence=confidence,
        reasoning_summary_zh=data.get("reasoning_summary_zh"),
        source_url=candidate.get("source_url"),
        source_type=candidate.get("source_type"),
        title=candidate.get("title"),
        prompt_version=prompt_version,
        model=model,
        created_at=utc_now_iso(),
    )


def run_pain_extraction(
    candidates: list[dict],
    relevance_results: list[dict],
    llm_client=None,
    config_path: Path | None = None,
    max_items: int | None = None,
    output_path: Path | None = None,
) -> list[ExtractedPainItem]:
    cfg = _load_config(config_path)
    limits = cfg.get("limits", {})
    max_items = max_items or int(limits.get("max_items", 150))
    max_chars = int(limits.get("max_raw_text_chars", 6000))
    min_score = float(limits.get("min_relevance_score_for_extraction", 0.45))
    cache_cfg = cfg.get("cache", {})
    use_cache = bool(cache_cfg.get("enabled", True))
    prompt_version = str(cache_cfg.get("prompt_version", "pain_extraction_v1"))
    run_scope = str(cache_cfg.get("run_scope", "demand_radar_mvp_b"))
    cache_dir = Path(str(cache_cfg.get("cache_dir", ".llm_cache/mvp_b")))

    rel_map = {r.get("candidate_id"): r for r in relevance_results}
    model_name = getattr(llm_client, "model", None) if llm_client else None

    items: list[ExtractedPainItem] = []
    pain_ids = next_ids("pain_", [], len(candidates))

    processed = 0
    for i, candidate in enumerate(candidates):
        if processed >= max_items:
            break

        cid = candidate.get("candidate_id", f"cand_{i}")
        rel = rel_map.get(cid, {})
        rel_decision = rel.get("relevance_decision", "exclude")
        rel_score = float(rel.get("relevance_score", 0.0))

        # Skip if excluded or score too low
        if rel_decision == "exclude" or rel_score < min_score:
            items.append(_reject_item(
                pain_ids[i], cid,
                f"domain relevance excluded or score too low ({rel_score:.2f})",
                candidate.get("source_url"), candidate.get("source_type"), candidate.get("title"),
                model=model_name,
            ))
            continue

        if llm_client is None:
            items.append(_reject_item(
                pain_ids[i], cid,
                "no LLM client configured",
                candidate.get("source_url"), candidate.get("source_type"), candidate.get("title"),
            ))
            continue

        system_p, user_p = _build_extraction_prompt(candidate, rel, max_chars)

        # Cache key
        input_hash = hashlib.sha256((cid + user_p[:200]).encode()).hexdigest()[:16]
        cache_file = cache_dir / f"pain_{prompt_version}_{input_hash}.json"
        cache_file.parent.mkdir(parents=True, exist_ok=True)

        data = None
        if use_cache and cache_file.exists():
            try:
                data = json.loads(cache_file.read_text(encoding="utf-8"))
            except Exception:
                data = None

        if data is None:
            # Try LLM with one retry
            last_error = None
            for attempt in range(2):
                try:
                    raw = llm_client.complete(system_p, user_p)
                    data = _parse_extraction_response(raw)
                    break
                except Exception as exc:
                    last_error = exc
                    data = None

            if data is None:
                items.append(_reject_item(
                    pain_ids[i], cid,
                    f"LLM extraction failed after retry: {last_error}",
                    candidate.get("source_url"), candidate.get("source_type"), candidate.get("title"),
                    model=model_name,
                ))
                processed += 1
                continue

            if use_cache:
                try:
                    cache_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
                except Exception:
                    pass

        try:
            item = _build_pain_item_from_data(pain_ids[i], candidate, data, model_name, prompt_version)
        except Exception as exc:
            items.append(_reject_item(
                pain_ids[i], cid,
                f"Pydantic validation error: {exc}",
                candidate.get("source_url"), candidate.get("source_type"), candidate.get("title"),
                model=model_name,
            ))
            processed += 1
            continue

        items.append(item)
        processed += 1

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            "\n".join(it.model_dump_json() for it in items) + "\n",
            encoding="utf-8",
        )

    return items