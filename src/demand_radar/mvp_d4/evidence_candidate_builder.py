"""MVP-D4: Build Radar EvidenceCandidates using Foundation WebExtraction."""
from __future__ import annotations
import json
from pathlib import Path
from demand_radar.acquisition.acquisition_schema import EvidenceCandidate
from demand_radar.state.raw_store import utc_now_iso
from opc_foundation.run.id_generator import new_id

_MIN_FULL_PAGE_CHARS = 200


def build_candidates(
    mapped_results: list[dict],
    domain_id: str = "ai_investment_tracking",
    domain_title_zh: str = "\u6295\u8d44\u4eba/\u7814\u7a76\u5458AI\u4ea7\u4e1a\u8ddf\u8e2a",
    use_foundation_extraction: bool = True,
    extraction_timeout: int = 10,
    output_path: Path | None = None,
) -> list[EvidenceCandidate]:
    candidates: list[EvidenceCandidate] = []
    now = utc_now_iso()
    for r in mapped_results:
        url = r.get("url", "")
        raw_text = ""
        raw_text_source = "snippet_only"
        if use_foundation_extraction and url:
            try:
                from demand_radar.mvp_d4.foundation_search_adapter import extract_page_foundation
                result = extract_page_foundation(url, timeout=extraction_timeout)
                if result.success and result.text and len(result.text.strip()) >= _MIN_FULL_PAGE_CHARS:
                    raw_text = result.text.strip()[:8000]
                    raw_text_source = "full_page"
            except Exception:
                pass
        if not raw_text:
            raw_text = r.get("snippet") or ""
            raw_text_source = "snippet_only"
        meta = {
            "provider": r.get("provider", ""),
            "query_id": r.get("query_id", ""),
            "seed_id": r.get("seed_id", ""),
            "pain_item_id": r.get("pain_item_id"),
            "query": r.get("query", ""),
            "query_type": r.get("query_type", ""),
            "search_rank": r.get("rank", 0),
            "result_domain": r.get("result_domain", ""),
            "raw_text_source": raw_text_source,
            "foundation_search": True,
        }
        cand = EvidenceCandidate(
            candidate_id=new_id("cand"),
            raw_signal_id=r.get("result_id", new_id("rsig")),
            source_id=f"foundation_search_{r.get('provider','')}",
            source_type="web_search",
            source_name=r.get("provider", ""),
            source_url=url,
            title=r.get("title"),
            raw_text=raw_text,
            domain_id=domain_id,
            domain_title_zh=domain_title_zh,
            collection_query=r.get("query"),
            fetched_at=now,
            source_weight=0.65,
            validation_status="valid" if raw_text else "warning",
            metadata=meta,
        )
        candidates.append(cand)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            for c in candidates:
                f.write(c.model_dump_json() + "\n")
    return candidates
