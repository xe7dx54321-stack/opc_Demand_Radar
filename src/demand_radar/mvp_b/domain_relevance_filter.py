"""MVP-B: Rule-based + LLM domain relevance filter."""
from __future__ import annotations
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from demand_radar.mvp_b.domain_relevance_schema import DomainRelevanceResult
from demand_radar.state.raw_store import next_ids, utc_now_iso

_CONFIG_PATH = Path("configs/domain_relevance_config.yaml")
_CACHE_DIR = Path(".llm_cache/mvp_b")


def _load_config(config_path: Path | None = None) -> dict[str, Any]:
    p = config_path or _CONFIG_PATH
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f).get("domain_relevance", {})


def _clean(text: str) -> str:
    t = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", t).strip().lower()


def _rule_score(candidate: dict, cfg: dict) -> tuple[float, str | None]:
    """Return (score, stop_reason). stop_reason signals early decision."""
    title = _clean((candidate.get("title") or ""))
    raw = _clean((candidate.get("raw_text") or ""))
    combined = title + " " + raw[:2000]

    score = 0.0

    neg_kws = [k.lower() for k in cfg.get("negative_keywords", [])]
    for kw in neg_kws:
        if kw in combined:
            score -= 0.40

    strong_kws = [k.lower() for k in cfg.get("strong_positive_keywords", [])]
    for kw in strong_kws:
        if kw in combined:
            score += 0.25

    weak_kws = [k.lower() for k in cfg.get("weak_positive_keywords", [])]
    for kw in weak_kws:
        if kw in combined:
            score += 0.10

    workflows = [w.lower() for w in cfg.get("target_workflows", [])]
    for wf in workflows:
        if wf in combined:
            score += 0.20
            break

    personas = [p.lower() for p in cfg.get("target_personas", [])]
    for pe in personas:
        if pe in combined:
            score += 0.20
            break

    stype = candidate.get("source_type", "")
    if stype in ("community_discussion", "github_issue"):
        score += 0.05

    return max(0.0, min(1.0, score)), None


def _make_llm_relevance_prompt(candidate: dict, cfg: dict) -> tuple[str, str]:
    domain_title = cfg.get("domain_title_zh", "AI Investment Tracking")
    personas = ", ".join(cfg.get("target_personas", [])[:6])
    raw_excerpt = (candidate.get("raw_text") or "")[:800]
    cid = candidate.get("candidate_id", "")
    title = candidate.get("title") or "(no title)"
    source_type = candidate.get("source_type", "")
    source_url = candidate.get("source_url", "")
    signals = str(candidate.get("detected_signal_types", []))

    system = (
        "You are a domain relevance classifier. Classify whether the evidence candidate "
        f"is relevant to: {domain_title}. Output ONLY valid JSON."
    )
    user = (
        f"Domain: {domain_title}\nTarget personas: {personas}\n\n"
        f"Candidate:\ntitle: {title}\nsource_type: {source_type}\n"
        f"source_url: {source_url}\ndetected_signal_types: {signals}\n"
        f"raw_text (first 800 chars):\n{raw_excerpt}\n\n"
        f'Output JSON:\n{{"candidate_id": "{cid}", "relevance_decision": "include | uncertain | exclude", '
        f'"relevance_score": 0.0, "matched_persona": null, "matched_workflow": null, '
        f'"domain_reason_zh": null, "exclude_reason_zh": null}}'
    )
    return system, user


def _parse_llm_relevance(raw: str) -> dict[str, Any]:
    text = raw.strip()
    # strip markdown fences
    text = re.sub(r"```(?:json)?\s*", "", text).replace("```", "")
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start:end + 1]
    return json.loads(text)


def run_domain_relevance_filter(
    candidates: list[dict],
    config_path: Path | None = None,
    llm_client=None,
    use_llm_for_uncertain: bool = True,
    output_path: Path | None = None,
) -> list[DomainRelevanceResult]:
    cfg = _load_config(config_path)
    include_threshold = float(cfg.get("thresholds", {}).get("include", 0.65))
    uncertain_threshold = float(cfg.get("thresholds", {}).get("uncertain", 0.45))

    results: list[DomainRelevanceResult] = []
    result_ids = next_ids("rel_", [], len(candidates))

    for i, candidate in enumerate(candidates):
        cid = candidate.get("candidate_id", f"cand_{i}")
        rule_score, _ = _rule_score(candidate, cfg)

        decision = "uncertain"
        prompt_version = "rule_only"
        model_name = None
        matched_persona = None
        matched_workflow = None
        domain_reason = None
        exclude_reason = None
        final_score = rule_score

        if rule_score >= include_threshold:
            decision = "include"
            domain_reason = f"规则评分 {rule_score:.2f} >= {include_threshold}"
        elif rule_score < uncertain_threshold:
            decision = "exclude"
            exclude_reason = f"规则评分 {rule_score:.2f} < {uncertain_threshold}，无相关关键词命中"
        else:
            # Uncertain: try LLM
            if llm_client is not None and use_llm_for_uncertain:
                prompt_version = "domain_relevance_v1"
                system_p, user_p = _make_llm_relevance_prompt(candidate, cfg)
                try:
                    cache_key = hashlib.sha256(
                        (cid + user_p[:200]).encode()
                    ).hexdigest()[:16]
                    cache_file = _CACHE_DIR / f"rel_{cache_key}.json"
                    cache_file.parent.mkdir(parents=True, exist_ok=True)

                    if cache_file.exists():
                        data = json.loads(cache_file.read_text(encoding="utf-8"))
                    else:
                        raw = llm_client.complete(system_p, user_p)
                        data = _parse_llm_relevance(raw)
                        cache_file.write_text(
                            json.dumps(data, ensure_ascii=False), encoding="utf-8"
                        )

                    decision = data.get("relevance_decision", "uncertain")
                    final_score = float(data.get("relevance_score", rule_score))
                    final_score = max(0.0, min(1.0, final_score))
                    matched_persona = data.get("matched_persona")
                    matched_workflow = data.get("matched_workflow")
                    domain_reason = data.get("domain_reason_zh")
                    exclude_reason = data.get("exclude_reason_zh")
                    model_name = getattr(llm_client, "model", None)
                    prompt_version = "domain_relevance_v1_llm"
                except Exception as exc:
                    exclude_reason = f"LLM failed, rule score uncertain: {exc}"
                    decision = "uncertain"

        # Safety: ensure required fields for validator
        if decision == "include" and not domain_reason:
            domain_reason = f"规则/LLM判定相关: score={final_score:.2f}"
        if decision == "exclude" and not exclude_reason:
            exclude_reason = f"规则/LLM判定不相关: score={final_score:.2f}"

        results.append(DomainRelevanceResult(
            result_id=result_ids[i],
            candidate_id=cid,
            relevance_decision=decision,
            relevance_score=final_score,
            matched_persona=matched_persona,
            matched_workflow=matched_workflow,
            domain_reason_zh=domain_reason,
            exclude_reason_zh=exclude_reason,
            source_type=candidate.get("source_type"),
            source_url=candidate.get("source_url"),
            prompt_version=prompt_version,
            model=model_name,
            created_at=utc_now_iso(),
        ))

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            "\n".join(r.model_dump_json() for r in results) + "\n",
            encoding="utf-8",
        )

    return results