"""MVP-D: Generate targeted search queries from reviewed pain seeds."""
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path

import yaml

from demand_radar.mvp_d.seed_schema import ReviewedPainSeed, SeededQuery
from demand_radar.state.raw_store import next_ids, utc_now_iso

_CONFIG_PATH = Path("configs/seeded_expansion_config.yaml")

_HN_CONNECTORS = {"hacker_news"}
_GH_CONNECTORS = {"github_issues"}
_RSS_CONNECTORS = {"rss"}


def _load_cfg(p: Path | None = None) -> dict:
    cfg_path = p or _CONFIG_PATH
    with open(cfg_path, encoding="utf-8") as f:
        return yaml.safe_load(f).get("seeded_expansion", {})


def _persona_terms(seed: ReviewedPainSeed) -> list[str]:
    terms = []
    if seed.persona:
        p = seed.persona.lower()
        if "vc" in p or "venture" in p:
            terms += ["VC analyst", "venture capital analyst", "VC due diligence"]
        elif "investment" in p or "investor" in p:
            terms += ["investment researcher", "investment analyst workflow"]
        elif "financial" in p:
            terms += ["financial analyst", "equity research analyst"]
        elif "market" in p:
            terms += ["market researcher", "market intelligence analyst"]
        elif "startup" in p or "scout" in p:
            terms += ["startup scout", "deal sourcing analyst"]
        else:
            terms += [seed.persona]
    if not terms:
        terms = ["investment researcher", "VC analyst"]
    return terms[:2]


def _workflow_terms(seed: ReviewedPainSeed) -> list[str]:
    wf = (seed.workflow_stage or "").lower()
    mapping = {
        "company_tracking": ["company tracking", "portfolio monitoring"],
        "deal_sourcing": ["deal sourcing", "startup screening"],
        "due_diligence": ["due diligence", "company research"],
        "investment_research": ["investment research", "equity research"],
        "market_monitoring": ["market monitoring", "industry tracking"],
        "memo_preparation": ["investment memo", "research report"],
        "portfolio_tracking": ["portfolio monitoring", "company update tracking"],
    }
    for key, vals in mapping.items():
        if key in wf or wf in key:
            return vals
    return ["investment research workflow", "analyst research process"]


def _pain_terms(seed: ReviewedPainSeed) -> list[str]:
    terms = []
    pt = (seed.pain_type or "").lower()
    if "scatter" in pt or "information" in pt:
        terms += ["information scattered", "data fragmented"]
    elif "manual" in pt or "workflow" in pt:
        terms += ["manual workflow", "time-consuming research"]
    elif "verification" in pt or "cost" in pt:
        terms += ["verification overhead", "research cost"]
    elif "tool_fragment" in pt or "fragment" in pt:
        terms += ["tool fragmentation", "workflow integration"]
    elif "signal" in pt or "noise" in pt:
        terms += ["signal noise", "information overload"]
    else:
        terms += ["workflow pain", "research bottleneck"]
    # Add from pain description
    desc = (seed.pain_description_zh or "")
    if "spreadsheet" in desc.lower() or "excel" in desc.lower():
        terms += ["spreadsheet pain", "Excel limitation"]
    elif "manual" in desc.lower():
        terms += ["manual process", "time-consuming"]
    return terms[:2]


def _competitor_terms(seed: ReviewedPainSeed) -> list[str]:
    return [
        "investment research software alternative",
        "competitor to Bloomberg research tool",
    ]


def _problem_phrases(seed: ReviewedPainSeed) -> list[str]:
    wf_terms = _workflow_terms(seed)
    p_terms = _pain_terms(seed)
    return [
        f'"{wf_terms[0]}" "problem"',
        f'"{p_terms[0]}" "analyst"',
    ]


def _workaround_phrases(seed: ReviewedPainSeed) -> list[str]:
    return [
        '"investment research" "spreadsheet" workaround',
        '"due diligence" "manual" "time"',
    ]


def generate_queries(
    seeds: list[ReviewedPainSeed],
    config_path: Path | None = None,
    output_path: Path | None = None,
    report_path: Path | None = Path("outputs/mvp_d/seeded_query_plan_report.md"),
    max_queries_total: int | None = None,
) -> list[SeededQuery]:
    cfg = _load_cfg(config_path)
    qgen_cfg = cfg.get("query_generation", {})
    max_q = int(qgen_cfg.get("max_queries_per_seed", 8))
    connectors = cfg.get("acquisition", {}).get("connectors", ["hacker_news", "github_issues", "rss"])
    out_path = output_path or Path(cfg.get("output", {}).get("query_plan_path", "data/processed/mvp_d/seeded_query_plan.jsonl"))

    queries: list[SeededQuery] = []
    now = utc_now_iso()

    for seed in seeds:
        seed_queries: list[tuple[str, str, str, str]] = []
        # (connector, query, query_type, expected_signal_type)

        persona_t = _persona_terms(seed)
        workflow_t = _workflow_terms(seed)
        pain_t = _pain_terms(seed)
        competitor_t = _competitor_terms(seed)
        problem_t = _problem_phrases(seed)
        workaround_t = _workaround_phrases(seed)

        # persona_workflow queries -> HN + GitHub
        for pt in persona_t[:1]:
            for wt in workflow_t[:1]:
                q = f'"{pt}" "{wt}"'
                seed_queries.append(("hacker_news", q, "persona_workflow", "pain"))
                seed_queries.append(("github_issues", f"{pt} {wt} problem", "persona_workflow", "complaint"))

        # pain_expression queries -> HN + GitHub
        for pt in pain_t[:1]:
            seed_queries.append(("hacker_news", f'"{pt}" investment analyst', "pain_expression", "pain"))
            seed_queries.append(("github_issues", f"{pt} investment research", "pain_expression", "complaint"))

        # workaround_phrase queries -> HN
        for wt in workaround_t[:1]:
            seed_queries.append(("hacker_news", wt, "workaround_phrase", "workaround"))

        # competitor_alternative -> HN
        for ct in competitor_t[:1]:
            seed_queries.append(("hacker_news", ct, "competitor_alternative", "comparison"))

        # problem_phrase -> GitHub
        for pbt in problem_t[:1]:
            seed_queries.append(("github_issues", pbt.replace('"', ""), "problem_phrase", "complaint"))

        # rss: use workflow + pain combo
        if "rss" in connectors:
            rss_q = f"{workflow_t[0]} AI tool"
            seed_queries.append(("rss", rss_q, "persona_workflow", "workflow"))

        # Limit per seed
        seed_queries = seed_queries[:max_q]

        q_ids = next_ids(f"query_{seed.seed_id}_", [], len(seed_queries))
        for i, (connector, q_str, q_type, sig_type) in enumerate(seed_queries):
            if connector not in connectors:
                continue
            sq = SeededQuery(
                query_id=q_ids[i],
                seed_id=seed.seed_id,
                pain_item_id=seed.pain_item_id,
                connector=connector,
                query=q_str,
                query_type=q_type,
                expected_signal_type=sig_type,
                priority=seed.expansion_priority,
                created_at=now,
            )
            queries.append(sq)

    if max_queries_total is not None:
        queries = queries[:max_queries_total]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for q in queries:
            f.write(q.model_dump_json() + "\n")

    if report_path is not None:
        build_seeded_query_plan_report(queries, report_path)

    return queries


def build_seeded_query_plan_report(
    queries: list[SeededQuery],
    output_path: Path = Path("outputs/mvp_d/seeded_query_plan_report.md"),
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    by_seed = Counter(q.seed_id for q in queries)
    by_connector = Counter(q.connector for q in queries)
    by_type = Counter(q.query_type for q in queries)
    lines = [
        "# MVP-D Seeded Query Plan Report",
        "",
        "## Summary",
        f"- total_queries: {len(queries)}",
        f"- queries_by_seed: {json.dumps(dict(by_seed), ensure_ascii=False)}",
        f"- queries_by_connector: {json.dumps(dict(by_connector), ensure_ascii=False)}",
        f"- queries_by_type: {json.dumps(dict(by_type), ensure_ascii=False)}",
        "",
        "## Query Examples",
        "",
    ]
    for query in queries[:20]:
        lines.append(
            "- "
            f"{query.query_id} | seed={query.seed_id} | pain={query.pain_item_id} | "
            f"{query.connector} | {query.query_type} | {query.query}"
        )
    if not queries:
        lines.append("No seeded queries generated.")
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return output_path
