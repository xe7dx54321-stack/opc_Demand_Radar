"""MVP-B: Pain extraction runner with caching, retry, and quote validation."""
from __future__ import annotations
import hashlib
import json
import os
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
    prompt_version: str = "pain_extraction_v1",
    cache_hit: bool = False,
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
        prompt_version=prompt_version,
        created_at=utc_now_iso(),
        metadata={"cache_hit": cache_hit},
    )


def _normalize_text(text: str) -> str:
    """Normalise text for fuzzy quote matching."""
    t = re.sub(r"<[^>]+>", " ", text)  # strip HTML
    t = re.sub(r"&#x27;", "'", t)
    t = re.sub(r"&amp;", "&", t)
    t = re.sub(r"&quot;", '"', t)
    t = re.sub(r"&#x2F;", "/", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip().lower()


def _check_quote_in_raw_text(evidence_quote: str | None, raw_text: str) -> bool:
    """Return True if evidence_quote appears (normalised) in raw_text."""
    if not evidence_quote:
        return False
    norm_q = _normalize_text(evidence_quote)
    norm_r = _normalize_text(raw_text)
    if not norm_q or len(norm_q) < 10:
        return False
    # Check first 60 chars of quote are contained
    snippet = norm_q[:60]
    return snippet in norm_r


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
        rel_score = float(relevance.get("relevance_score", 0.0))

    system = (
        "You are a demand signal extraction specialist focused on the investment research, "
        "venture capital, and AI-investment-tracking domain. "
        "Extract structured pain signals from real-world web content.\n\n"
        "Core rules (must follow):\n"
        "1. Only extract information directly supported by the raw_text. Do NOT invent or embellish.\n"
        "2. evidence_quote MUST be verbatim text from raw_text. If no suitable quote exists, set should_extract=false.\n"
        "3. If raw_text is a product page with no user pain, set should_extract=false.\n"
        "4. evidence_strength='strong' only if ALL of: persona, workflow_stage, pain_description_zh, evidence_quote are present.\n"
        "5. If persona unclear, set persona_confidence <= 0.5 and do NOT use evidence_strength='strong'.\n"
        "6. paid_alternative and budget_signal: null if not explicitly mentioned.\n"
        "7. For off-domain content, set should_extract=false and evidence_strength='reject'.\n"
        "8. Output ONLY valid JSON. No markdown, no commentary."
    )
    user = (
        f"Domain: \u6295\u8d44\u4eba / \u7814\u7a76\u5458 AI \u4ea7\u4e1a\u8ddf\u8e2a\u4e0e\u9879\u76ee\u521d\u7b5b\n"
        f"Target personas: investor, VC analyst, PE analyst, investment researcher, market researcher, financial analyst, startup scout\n\n"
        f"Evidence candidate:\n"
        f"candidate_id: {cid}\n"
        f"title: {title}\n"
        f"source_type: {source_type}\n"
        f"source_url: {source_url}\n"
        f"domain_relevance: {rel_decision} (score: {rel_score:.2f})\n"
        f"detected_signal_types: {signals}\n\n"
        f"raw_text (up to {max_chars} chars):\n{raw_text}\n\n"
        f"Instructions:\n"
        f"- Read the raw_text carefully.\n"
        f"- Identify the primary pain point or demand signal relevant to investment research / AI-investment-tracking.\n"
        f"- Extract only what is directly stated or strongly implied in the text.\n"
        f"- evidence_quote must be a direct excerpt from the raw_text above.\n"
        f"- If the text is purely a product description with no user pain/workflow context, set should_extract=false.\n\n"
        f'Output this exact JSON structure:\n'
        f'{{"candidate_id": "{cid}", "should_extract": true, "reject_reason": null, '
        f'"persona": null, "persona_confidence": 0.0, "workflow_stage": null, "job_to_be_done": null, '
        f'"pain_type": null, "pain_description_zh": null, "evidence_quote": null, '
        f'"current_solution": null, "paid_alternative": null, "business_impact": null, '
        f'"time_cost_signal": null, "budget_signal": null, "commercial_signal_type": null, '
        f'"evidence_strength": "medium", "confidence": 0.0, "reasoning_summary_zh": null}}'
    )
    return system, user


def build_extraction_prompt(
    candidate: dict,
    relevance: dict | None,
    max_chars: int = 6000,
) -> tuple[str, str]:
    """Public wrapper used by MVP-D and tests."""
    return _build_extraction_prompt(candidate, relevance, max_chars=max_chars)


def make_default_pain_extraction_client():
    """Create the default real LLM client for pain extraction if configured."""
    provider = os.environ.get("DEMAND_RADAR_LLM_PROVIDER") or os.environ.get("LLM_PROVIDER") or "anthropic_compatible"
    from demand_radar.semantic_merge.llm_client import make_llm_client

    llm_conf = {
        "llm": {
            "base_url_env": "DEMAND_RADAR_LLM_BASE_URL",
            "api_key_env": "DEMAND_RADAR_LLM_API_KEY",
            "model": os.environ.get("DEMAND_RADAR_LLM_MODEL", "claude-sonnet-4-6"),
            "temperature": 0,
            "max_tokens": 4000,
        }
    }
    return make_llm_client(provider, llm_conf)


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
    prompt_version: str = "acquired_signal_pain_extraction_v1",
    cache_hit: bool = False,
    raw_text: str = "",
) -> ExtractedPainItem:
    should_extract = bool(data.get("should_extract", False))
    evidence_strength = str(data.get("evidence_strength") or "weak")
    confidence = float(data.get("confidence") or 0.0)
    confidence = max(0.0, min(1.0, confidence))
    evidence_quote = data.get("evidence_quote") or None
    reject_reason = data.get("reject_reason") or None

    # Rule: should_extract=True needs evidence_quote
    if should_extract and not evidence_quote:
        should_extract = False
        reject_reason = "evidence_quote missing in LLM output"
        evidence_strength = "reject"

    # Rule: should_extract=False needs reject_reason
    if not should_extract and not reject_reason:
        reject_reason = "LLM returned should_extract=false without reason"

    # Quote validation: check evidence_quote appears in raw_text
    quote_matched = False
    if should_extract and evidence_quote and raw_text:
        quote_matched = _check_quote_in_raw_text(evidence_quote, raw_text)
        if not quote_matched:
            # Downgrade strong to medium; downgrade medium to weak
            if evidence_strength == "strong":
                evidence_strength = "medium"
            elif evidence_strength == "medium":
                evidence_strength = "weak"
            # Record warning in metadata

    return ExtractedPainItem(
        pain_item_id=pain_item_id,
        candidate_id=candidate.get("candidate_id", ""),
        should_extract=should_extract,
        reject_reason=reject_reason,
        persona=data.get("persona"),
        persona_confidence=(
            float(data.get("persona_confidence") or 0.0)
            if data.get("persona_confidence") is not None else None
        ),
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
        metadata={
            "cache_hit": cache_hit,
            "quote_matched": quote_matched,
        },
    )


def run_pain_extraction(
    candidates: list[dict],
    relevance_results: list[dict],
    llm_client=None,
    config_path: Path | None = None,
    max_items: int | None = None,
    output_path: Path | None = None,
    cache_backend=None,
    prompt_version_override: str | None = None,
    run_scope_override: str | None = None,
) -> list[ExtractedPainItem]:
    cfg = _load_config(config_path)
    limits = cfg.get("limits", {})
    max_items = max_items or int(limits.get("max_items", 150))
    max_chars = int(limits.get("max_raw_text_chars", 6000))
    min_score = float(limits.get("min_relevance_score_for_extraction", 0.45))
    cache_cfg = cfg.get("cache", {})
    use_cache = bool(cache_cfg.get("enabled", True)) if cache_backend is None else bool(getattr(cache_backend, "enabled", True))
    prompt_version = str(prompt_version_override or cache_cfg.get("prompt_version", "acquired_signal_pain_extraction_v1"))
    run_scope = str(run_scope_override or cache_cfg.get("run_scope", "demand_radar_mvp_b_llm_pass"))
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
        raw_text = candidate.get("raw_text") or ""

        # Skip if excluded or score too low
        if rel_decision == "exclude" or rel_score < min_score:
            items.append(_reject_item(
                pain_ids[i], cid,
                f"domain relevance excluded or score too low ({rel_score:.2f})",
                candidate.get("source_url"), candidate.get("source_type"), candidate.get("title"),
                model=model_name, prompt_version=prompt_version,
            ))
            continue

        if llm_client is None:
            items.append(_reject_item(
                pain_ids[i], cid,
                "no LLM client configured",
                candidate.get("source_url"), candidate.get("source_type"), candidate.get("title"),
                prompt_version=prompt_version,
            ))
            continue

        system_p, user_p = _build_extraction_prompt(candidate, rel, max_chars)
        raw_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
        data = None
        cache_hit = False
        if cache_backend is not None:
            try:
                data = cache_backend.get(
                    candidate_id=cid,
                    provider=getattr(llm_client, "provider", "none") if llm_client else "none",
                    model=model_name or "none",
                    prompt_version=prompt_version,
                    run_scope=run_scope,
                    raw_hash=raw_hash,
                )
                cache_hit = data is not None
            except Exception:
                data = None
                cache_hit = False
        elif use_cache:
            input_hash = hashlib.sha256(
                (run_scope + prompt_version + cid + user_p[:500]).encode()
            ).hexdigest()[:20]
            cache_file = cache_dir / f"pain_{prompt_version}_{input_hash}.json"
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            if cache_file.exists():
                try:
                    data = json.loads(cache_file.read_text(encoding="utf-8"))
                    cache_hit = True
                except Exception:
                    data = None

        if data is None:
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
                    model=model_name, prompt_version=prompt_version,
                ))
                processed += 1
                continue

            if cache_backend is not None:
                try:
                    cache_backend.set(
                        candidate_id=cid,
                        provider=getattr(llm_client, "provider", "none") if llm_client else "none",
                        model=model_name or "none",
                        prompt_version=prompt_version,
                        run_scope=run_scope,
                        raw_hash=raw_hash,
                        result=data,
                    )
                except Exception:
                    pass
            elif use_cache:
                try:
                    cache_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
                except Exception:
                    pass

        try:
            item = _build_pain_item_from_data(
                pain_ids[i], candidate, data, model_name, prompt_version,
                cache_hit=cache_hit, raw_text=raw_text,
            )
            item.metadata = {
                **(item.metadata or {}),
                "cache_hit": cache_hit,
                "quote_matched": item.metadata.get("quote_matched") if item.metadata else False,
                "provider": getattr(llm_client, "provider", "none") if llm_client else "none",
                "run_scope": run_scope,
                "prompt_version": prompt_version,
                "raw_text_hash": raw_hash,
            }
        except Exception as exc:
            items.append(_reject_item(
                pain_ids[i], cid,
                f"Pydantic validation error: {exc}",
                candidate.get("source_url"), candidate.get("source_type"), candidate.get("title"),
                model=model_name, prompt_version=prompt_version,
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
