"""Pain-oriented query pattern library for MVP-D2."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QueryPattern:
    query_type: str
    template: str
    expected_signal_type: str
    priority: str = "medium"
    source_category: str = "user_discussion"
    connector: str = "hacker_news"


NEGATIVE_TERMS = [
    "recipe",
    "diet",
    "fitness",
    "game",
    "dating",
    "crypto trading bot",
    "casino",
    "generic chatbot",
    "tutorial",
    "hello world",
]


QUERY_PATTERNS: list[QueryPattern] = [
    QueryPattern("pain_phrase", '"{workflow}" "pain"', "pain", "high"),
    QueryPattern("pain_phrase", '"{workflow}" "problem"', "pain", "high"),
    QueryPattern("pain_phrase", '"{workflow}" "hard to"', "pain", "high"),
    QueryPattern("complaint_phrase", '"{persona}" "{workflow}" "frustrated"', "complaint", "high"),
    QueryPattern("complaint_phrase", '"{workflow}" "too time consuming"', "complaint", "high"),
    QueryPattern("workaround_phrase", '"{workflow}" "spreadsheet"', "workaround", "high"),
    QueryPattern("workaround_phrase", '"{workflow}" "Airtable"', "workaround", "medium"),
    QueryPattern("workaround_phrase", '"{workflow}" "Notion"', "workaround", "medium"),
    QueryPattern("manual_workflow", '"{workflow}" "manual"', "workflow", "high"),
    QueryPattern("spreadsheet_workaround", '"{persona}" "{workflow}" "spreadsheet"', "workaround", "high"),
    QueryPattern("job_to_be_done", '"{persona}" "need to" "{workflow}"', "workflow", "medium"),
    QueryPattern("job_to_be_done", '"{persona}" "trying to" "{workflow}"', "workflow", "medium"),
    QueryPattern("buying_intent", '"best tool for" "{workflow}"', "paid_signal", "medium"),
    QueryPattern("alternative_tool", '"alternative to" "{competitor_or_tool}"', "comparison", "medium"),
    QueryPattern("buying_intent", '"{workflow}" "software" "expensive"', "paid_signal", "medium"),
    QueryPattern("community_question", '"how do you" "{workflow}"', "workflow", "high"),
    QueryPattern("community_question", '"what do you use for" "{workflow}"', "workaround", "high"),
    QueryPattern("competitor_review", '"{competitor_or_tool}" "review" "expensive"', "comparison", "medium"),
]


DOMAIN_RECOMMENDED_QUERIES = [
    ('pain_phrase', '"investment research workflow" "spreadsheet"'),
    ('manual_workflow', '"investment research workflow" "manual"'),
    ('complaint_phrase', '"investment memo" "time consuming"'),
    ('spreadsheet_workaround', '"VC analyst" "due diligence" "spreadsheet"'),
    ('pain_phrase', '"VC analyst" "market research" "pain"'),
    ('complaint_phrase', '"portfolio monitoring" "too much information"'),
    ('pain_phrase', '"portfolio monitoring" "hard to track"'),
    ('manual_workflow', '"deal sourcing" "manual research"'),
    ('workaround_phrase', '"deal sourcing" "Airtable"'),
    ('complaint_phrase', '"startup screening" "too much time"'),
    ('spreadsheet_workaround', '"company tracking" "investment analyst" "spreadsheet"'),
    ('manual_workflow', '"market map" "maintain" "VC"'),
    ('manual_workflow', '"equity research" "data collection" "manual"'),
    ('pain_phrase', '"competitive intelligence" "hard to track"'),
    ('workaround_phrase', '"investment analyst" "research workflow" "Notion"'),
    ('buying_intent', '"due diligence" "research" "expensive"'),
    ('manual_workflow', '"market research" "analyst" "manual"'),
]


def workflow_terms(seed: dict) -> list[str]:
    raw = " ".join(
        str(seed.get(key) or "")
        for key in ("workflow_stage", "pain_description_zh", "title", "evidence_quote")
    ).lower()
    terms: list[str] = []
    mapping = [
        ("deal", ["deal sourcing", "startup screening"]),
        ("startup", ["startup screening", "company tracking"]),
        ("due diligence", ["due diligence", "investment research"]),
        ("memo", ["investment memo", "research memo"]),
        ("portfolio", ["portfolio monitoring", "company tracking"]),
        ("company", ["company tracking", "investment research workflow"]),
        ("market", ["market research", "market map"]),
        ("competitive", ["competitive intelligence", "market map"]),
        ("equity", ["equity research", "data collection"]),
        ("investment", ["investment research workflow", "investment memo"]),
    ]
    for needle, values in mapping:
        if needle in raw:
            terms.extend(values)
    terms.extend(["investment research workflow", "company tracking", "deal sourcing"])
    return _unique(terms)[:4]


def persona_terms(seed: dict) -> list[str]:
    raw = " ".join(
        str(seed.get(key) or "")
        for key in ("persona", "pain_description_zh", "title", "evidence_quote")
    ).lower()
    terms: list[str] = []
    if "vc" in raw or "venture" in raw:
        terms.extend(["VC analyst", "venture capital analyst"])
    if "equity" in raw or "stock" in raw:
        terms.extend(["equity research analyst", "investment analyst"])
    if "market" in raw:
        terms.extend(["market researcher", "investment analyst"])
    if "investor" in raw:
        terms.extend(["investor", "investment analyst"])
    terms.extend(["VC analyst", "investment analyst", "market researcher"])
    return _unique(terms)[:3]


def competitor_terms(seed: dict) -> list[str]:
    raw = " ".join(
        str(seed.get(key) or "")
        for key in ("pain_description_zh", "evidence_quote", "title")
    ).lower()
    terms: list[str] = []
    for term in ["bloomberg", "seeking alpha", "chatgpt", "perplexity", "notion", "airtable", "excel"]:
        if term in raw:
            terms.append(term.title() if term not in {"chatgpt"} else "ChatGPT")
    terms.extend(["Bloomberg Terminal", "PitchBook", "Airtable", "Notion"])
    return _unique(terms)[:3]


def source_category_for_query_type(query_type: str) -> str:
    if query_type in {"complaint_phrase", "community_question", "pain_phrase"}:
        return "user_discussion"
    if query_type in {"workaround_phrase", "manual_workflow", "spreadsheet_workaround"}:
        return "workaround_discussion"
    if query_type in {"buying_intent", "competitor_review", "alternative_tool"}:
        return "comparison_page"
    return "practitioner_blog"


def connector_for_query_type(query_type: str) -> str:
    if query_type in {"pain_phrase", "complaint_phrase", "community_question", "manual_workflow"}:
        return "hacker_news"
    if query_type in {"spreadsheet_workaround", "workaround_phrase"}:
        return "hacker_news"
    return "rss"


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        text = value.strip()
        if text and text not in result:
            result.append(text)
    return result
