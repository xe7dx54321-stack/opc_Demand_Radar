"""MVP-D3: Search provider client - Tavily/Brave with auto-detection."""
from __future__ import annotations
import os, urllib.request, json as _json
from demand_radar.mvp_d3.search_provider_schema import SearchResultItem
from demand_radar.state.raw_store import utc_now_iso
from opc_foundation.run.id_generator import new_id

_PROVIDER_ENV = [
    ("tavily",    "TAVILY_API_KEY"),
    ("brave",     "BRAVE_SEARCH_API_KEY"),
    ("serpapi",   "SERPAPI_API_KEY"),
    ("bing",      "BING_SEARCH_API_KEY"),
    ("google_cse","GOOGLE_CSE_API_KEY"),
]


def detect_provider() -> tuple[str | None, str | None]:
    for name, env in _PROVIDER_ENV:
        key = os.environ.get(env, "")
        if key:
            return name, key
    return None, None


class TavilyClient:
    provider_name = "tavily"
    def __init__(self, api_key: str, timeout: int = 20):
        self._key = api_key
        self._timeout = timeout
    def search(self, query: str, max_results: int = 5, query_id: str = "",
               seed_id: str = "", query_type: str = "") -> list[SearchResultItem]:
        payload = _json.dumps({"api_key": self._key, "query": query,
                               "max_results": max_results, "search_depth": "basic",
                               "include_answer": False}).encode()
        req = urllib.request.Request(
            "https://api.tavily.com/search", data=payload,
            headers={"Content-Type": "application/json"}, method="POST")
        now = utc_now_iso()
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            data = _json.loads(resp.read())
        results = []
        for i, r in enumerate(data.get("results", [])[:max_results]):
            results.append(SearchResultItem(
                result_id=new_id("sr"), provider="tavily",
                query_id=query_id, seed_id=seed_id, query=query, query_type=query_type,
                title=r.get("title"), url=r.get("url", ""),
                snippet=r.get("content") or r.get("snippet"),
                published_at=r.get("published_date"), rank=i+1,
                raw_provider_payload=r, created_at=now))
        return results


class BraveClient:
    provider_name = "brave"
    def __init__(self, api_key: str, timeout: int = 20):
        self._key = api_key
        self._timeout = timeout
    def search(self, query: str, max_results: int = 5, query_id: str = "",
               seed_id: str = "", query_type: str = "") -> list[SearchResultItem]:
        import urllib.parse
        params = urllib.parse.urlencode({"q": query, "count": max_results})
        req = urllib.request.Request(
            f"https://api.search.brave.com/res/v1/web/search?{params}",
            headers={"Accept": "application/json", "X-Subscription-Token": self._key})
        now = utc_now_iso()
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            data = _json.loads(resp.read())
        results = []
        for i, r in enumerate((data.get("web", {}).get("results") or [])[:max_results]):
            results.append(SearchResultItem(
                result_id=new_id("sr"), provider="brave",
                query_id=query_id, seed_id=seed_id, query=query, query_type=query_type,
                title=r.get("title"), url=r.get("url", ""),
                snippet=r.get("description"), rank=i+1,
                raw_provider_payload=r, created_at=now))
        return results


def make_search_client(provider: str | None = None, api_key: str | None = None):
    if provider is None:
        provider, api_key = detect_provider()
    if not provider or not api_key:
        return None
    if provider == "tavily":
        return TavilyClient(api_key)
    if provider == "brave":
        return BraveClient(api_key)
    return None
