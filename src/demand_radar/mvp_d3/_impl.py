"""MVP-D3: Normalizer, evidence builder, yield analyzer, report builder, pipeline."""
from __future__ import annotations
import json, re, subprocess, urllib.request
from collections import Counter
from pathlib import Path
from demand_radar.acquisition.acquisition_schema import EvidenceCandidate
from demand_radar.mvp_d3.search_provider_schema import SearchResultItem, MVP_D3_RunSummary
from demand_radar.mvp_d.real_signal_gate import run_gate as mvp_d_run_gate
from demand_radar.mvp_b.pain_extraction_runner import run_pain_extraction
from demand_radar.state.raw_store import utc_now_iso
from opc_foundation.run.id_generator import new_id

_BLOCK_DOMAINS = {"example.com", "example.org", "example.net"}


# ── Normalizer ──────────────────────────────────────────────────────────────
def normalize_results(results: list[SearchResultItem],
                      output_path: Path | None = None) -> list[SearchResultItem]:
    seen: set[str] = set()
    out: list[SearchResultItem] = []
    for r in results:
        url = r.url.strip()
        if not url or any(b in url.lower() for b in _BLOCK_DOMAINS) or url in seen:
            continue
        seen.add(url)
        out.append(r)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            for r in out:
                f.write(r.model_dump_json() + "\n")
    return out


# ── Evidence builder ─────────────────────────────────────────────────────────
def _fetch_page(url: str, timeout: int = 10) -> str | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "demand-radar-mvp-d3/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(65536)
            charset = resp.headers.get_content_charset("utf-8")
            text = raw.decode(charset, errors="replace")
            text = re.sub(r"<[^>]+>", " ", text)
            return re.sub(r"\s+", " ", text).strip()[:8000]
    except Exception:
        return None


def build_candidates(results: list[SearchResultItem], domain_id: str = "ai_investment_tracking",
                     domain_title_zh: str = "投资人/研究员AI产业跟踪",
                     fetch_pages: bool = True, fetch_timeout: int = 10,
                     output_path: Path | None = None) -> list[EvidenceCandidate]:
    candidates: list[EvidenceCandidate] = []
    now = utc_now_iso()
    for r in results:
        raw_text, src_type = "", "snippet_only"
        if fetch_pages:
            full = _fetch_page(r.url, timeout=fetch_timeout)
            if full and len(full.strip()) >= 200:
                raw_text, src_type = full, "full_page"
        if not raw_text:
            raw_text, src_type = (r.snippet or ""), "snippet_only"
        meta = {"provider": r.provider, "query_id": r.query_id, "seed_id": r.seed_id,
                "query": r.query, "query_type": r.query_type,
                "search_rank": r.rank, "raw_text_source": src_type}
        cand = EvidenceCandidate(
            candidate_id=new_id("cand"), raw_signal_id=r.result_id,
            source_id=f"search_{r.provider}", source_type="web_search",
            source_name=r.provider, source_url=r.url, title=r.title,
            raw_text=raw_text, domain_id=domain_id, domain_title_zh=domain_title_zh,
            collection_query=r.query, fetched_at=now, source_weight=0.6,
            validation_status="valid" if raw_text else "warning", metadata=meta)
        candidates.append(cand)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            for c in candidates:
                f.write(c.model_dump_json() + "\n")
    return candidates


# ── Yield analyzer ───────────────────────────────────────────────────────────
def analyze_yield(selected_queries, search_results, gate_allowed, pain_items,
                  output_path: Path | None = None) -> dict:
    extracted = [p for p in pain_items if getattr(p,"should_extract",False)]
    sel_llm = len(pain_items)
    yield_rate = len(extracted)/sel_llm if sel_llm > 0 else 0.0
    strong = sum(1 for p in pain_items if getattr(p,"evidence_strength","")=="strong")
    medium = sum(1 for p in pain_items if getattr(p,"evidence_strength","")=="medium")
    weak   = sum(1 for p in pain_items if getattr(p,"evidence_strength","")=="weak")
    qtype_r = Counter(getattr(r,"query_type","unknown") for r in search_results)
    seed_r  = Counter(getattr(r,"seed_id","unknown") for r in search_results)
    lines = ["# MVP-D3 Search Yield Report\n",
             f"- yield_rate: {yield_rate:.2%}", f"- selected_for_llm: {sel_llm}",
             f"- should_extract_true: {len(extracted)}",
             f"- strong: {strong}", f"- medium: {medium}", f"- weak: {weak}",
             "\n## By Query Type"] + [f"- {k}: {v}" for k,v in qtype_r.most_common()] + \
            ["\n## By Seed"] + [f"- {k}: {v}" for k,v in seed_r.most_common()]
    report = "\n".join(lines) + "\n"
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
    return {"total_queries": len(selected_queries), "search_results": len(search_results),
            "unique_urls": len({getattr(r,"url","") for r in search_results}),
            "gate_allowed": len(gate_allowed), "selected_for_llm": sel_llm,
            "should_extract_true": len(extracted), "strong": strong,
            "medium": medium, "weak": weak, "yield_rate": yield_rate}


# ── Reports ──────────────────────────────────────────────────────────────────
def _git_commit() -> str:
    try:
        return subprocess.check_output(["git","rev-parse","--short","HEAD"],text=True).strip()
    except Exception:
        return "unknown"


def build_gate_report(gate_allowed, gate_blocked, output_path: Path | None = None) -> str:
    op = output_path or Path("outputs/mvp_d3/search_gate_report.md")
    total = len(gate_allowed)+len(gate_blocked)
    reasons = Counter(r.block_reason for r in gate_blocked if r.block_reason)
    lines = ["# MVP-D3 Search Gate Report",
             f"- total_candidates: {total}", f"- allowed: {len(gate_allowed)}",
             f"- blocked: {len(gate_blocked)}", "## Block Reasons"] + \
            [f"- {r}: {c}" for r,c in reasons.most_common()]
    report = "\n".join(lines)+"\n"
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(report, encoding="utf-8")
    return report


def build_summary_report(pilot: dict, output_path: Path | None = None) -> str:
    op = output_path or Path("outputs/mvp_d3/mvp_d3_summary_report.md")
    now = utc_now_iso(); commit = _git_commit()
    provider = pilot.get("provider","none"); blocked = pilot.get("blocked_reason")
    should_ext = pilot.get("should_extract_true",0); sel_llm = pilot.get("selected_for_llm",0)
    gate_ok = pilot.get("gate_allowed",0)
    yield_rate = should_ext/sel_llm if sel_llm>0 else 0.0
    eng = "partial" if (blocked or gate_ok==0) else "pass"
    prod = "blocked" if blocked else ("pass" if should_ext>=5 else "partial" if should_ext>0 else "blocked")
    lines = ["# MVP-D3 Search Provider Pilot Summary","",
             "## Run Metadata", f"- generated_at: {now}", f"- radar_commit: {commit}",
             "- foundation_commit: b6d23bc", f"- provider: {provider}",
             f"- model: {pilot.get('model','none')}", f"- real_llm_run: {pilot.get('real_llm_run',False)}","",
             "## Provider Detection", f"- detected_provider: {provider}",
             f"- provider_available: {not blocked}", f"- blocked_reason: {blocked or 'none'}","",
             "## Query Selection", f"- selected_queries: {pilot.get('selected_queries',0)}","",
             "## Search Results",
             f"- total_search_results: {pilot.get('total_search_results',0)}",
             f"- unique_urls: {pilot.get('unique_urls',0)}","",
             "## Evidence Build & Gate",
             f"- evidence_candidates: {pilot.get('evidence_candidates',0)}",
             f"- gate_allowed: {gate_ok}", f"- gate_blocked: {pilot.get('gate_blocked',0)}",
             f"- snippet_only: {pilot.get('snippet_only_count',0)}",
             f"- full_page: {pilot.get('full_page_count',0)}","",
             "## LLM Extraction", f"- selected_for_llm: {sel_llm}",
             f"- should_extract_true: {should_ext}", f"- strong: {pilot.get('strong',0)}",
             f"- medium: {pilot.get('medium',0)}", f"- weak: {pilot.get('weak',0)}",
             f"- failures: {pilot.get('failures',0)}","",
             "## Yield", f"- yield_rate: {yield_rate:.2%}","",
             "## Top Pain Signals"]
    for p in [x for x in pilot.get("pain_items",[]) if getattr(x,"should_extract",False)][:5]:
        lines.append(f"- {getattr(p,'title','?')[:80]} | {getattr(p,'evidence_strength','?')}")
    lines += ["","## Acceptance",
              f"- engineering_acceptance: {eng}", f"- product_acceptance: {prod}",
              f"- can_enter_second_review: {should_ext>=3}",
              f"- can_enter_foundation_source_upgrade: {blocked is not None}",
              f"- reason: {blocked or f'yield_rate={yield_rate:.2%}'}","","## Errors"] + \
             [f"- {e}" for e in (pilot.get("errors") or [])[:5]]
    report = "\n".join(lines)+"\n"
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(report, encoding="utf-8")
    return report
