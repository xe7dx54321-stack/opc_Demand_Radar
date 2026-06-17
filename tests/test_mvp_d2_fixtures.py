import json
from pathlib import Path


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + ("\n" if rows else ""),
        encoding="utf-8",
    )


def write_d2_fixture(tmp_path: Path, count: int = 3) -> dict[str, Path]:
    candidates = []
    pain_items = []
    queries = [
        {
            "query_id": "query_1",
            "seed_id": "seed_1",
            "pain_item_id": "pain_seed_1",
            "connector": "github_issues",
            "query": "investment researcher workflow problem",
            "query_type": "persona_workflow",
            "expected_signal_type": "complaint",
            "priority": "high",
            "negative_terms": [],
            "created_at": "2026-01-01T00:00:00Z",
            "metadata": {},
        },
        {
            "query_id": "query_2",
            "seed_id": "seed_1",
            "pain_item_id": "pain_seed_1",
            "connector": "rss",
            "query": "investment research workflow AI tool",
            "query_type": "persona_workflow",
            "expected_signal_type": "workflow",
            "priority": "medium",
            "negative_terms": [],
            "created_at": "2026-01-01T00:00:00Z",
            "metadata": {},
        },
    ]
    for index in range(count):
        query_id = "query_1" if index < count - 1 else "query_2"
        source_type = "github_issue" if query_id == "query_1" else "rss"
        raw_text = (
            "Daily Content Summary with generated report and executive summary. "
            if source_type == "rss"
            else "Implementation issue about API worker runtime schema bug and metadata build. "
        ) * 30
        candidates.append(
            {
                "candidate_id": f"cand_{index+1}",
                "raw_signal_id": f"raw_{index+1}",
                "source_id": "src",
                "source_type": source_type,
                "source_name": "Fixture",
                "source_url": f"https://example.org/real/{index+1}".replace("example.org", "github.com" if source_type == "github_issue" else "news.example.com"),
                "title": "Technical implementation issue" if source_type == "github_issue" else "Daily Content Summary",
                "raw_text": raw_text,
                "domain_id": "ai_investment_tracking",
                "domain_title_zh": "投资研究",
                "collection_query": queries[0]["query"],
                "fetched_at": "2026-01-01T00:00:00Z",
                "source_weight": 0.8,
                "validation_status": "valid",
                "validation_reasons": [],
                "detected_signal_types": [],
                "include_in_evidence_pack": True,
                "metadata": {
                    "seed_id": "seed_1",
                    "pain_item_id": "pain_seed_1",
                    "seed_query_id": query_id,
                    "expansion_source": "github_issues" if source_type == "github_issue" else "rss",
                },
            }
        )
        pain_items.append(
            {
                "pain_item_id": f"pain_{index+1}",
                "candidate_id": f"cand_{index+1}",
                "should_extract": False,
                "reject_reason": "domain relevance excluded or score too low (0.05)",
                "evidence_strength": "reject",
                "confidence": 0.0,
                "source_url": candidates[-1]["source_url"],
                "source_type": source_type,
                "title": candidates[-1]["title"],
                "prompt_version": "acquired_signal_pain_extraction_v1",
                "model": "claude-sonnet-4-6",
                "created_at": "2026-01-01T00:00:00Z",
                "metadata": {"seed_id": "seed_1", "pain_item_id": "pain_seed_1", "seed_query_id": query_id},
            }
        )
    seeds = [
        {
            "seed_id": "seed_1",
            "pain_item_id": "pain_seed_1",
            "candidate_id": "base_cand",
            "title": "Investment research workflow pain",
            "source_url": "https://news.ycombinator.com/item?id=1",
            "source_type": "community_discussion",
            "persona": "VC analyst",
            "workflow_stage": "deal_sourcing",
            "pain_type": "manual_workflow",
            "pain_description_zh": "VC analyst manually tracks companies in spreadsheets.",
            "evidence_quote": "manual tracking is time consuming",
            "true_pain": True,
            "commercial_potential": "high",
            "evidence_quality": "strong",
            "action_decision": "needs_more_evidence",
            "expansion_priority": "high",
            "seed_reason_zh": "true pain",
            "created_at": "2026-01-01T00:00:00Z",
            "metadata": {},
        }
    ]
    paths = {
        "candidates": tmp_path / "candidates.jsonl",
        "pain_items": tmp_path / "pain.jsonl",
        "seeds": tmp_path / "seeds.jsonl",
        "queries": tmp_path / "queries.jsonl",
    }
    write_jsonl(paths["candidates"], candidates)
    write_jsonl(paths["pain_items"], pain_items)
    write_jsonl(paths["seeds"], seeds)
    write_jsonl(paths["queries"], queries)
    return paths
