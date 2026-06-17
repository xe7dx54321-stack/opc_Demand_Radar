"""MVP-D4: Adapter wrapping Foundation v0.1.2 search runtime."""
from __future__ import annotations
from packaging.version import Version


_REQUIRED = "0.1.2"


def check_foundation_version() -> tuple[bool, str]:
    try:
        import opc_foundation
        ver = opc_foundation.__version__
        ok = Version(ver) >= Version(_REQUIRED)
        return ok, ver
    except Exception as exc:
        return False, str(exc)


def get_registry():
    from opc_foundation.search import SearchProviderRegistry
    return SearchProviderRegistry.from_env()


def detect_provider(registry=None) -> str | None:
    reg = registry or get_registry()
    prov = reg.get_preferred_provider()
    return prov.provider_name if prov else None


def run_foundation_search(
    query: str,
    max_results: int = 5,
    registry=None,
) -> list:
    """Run search via Foundation runtime. Returns list of SearchResult."""
    from opc_foundation.search import run_search
    result = run_search(query=query, max_results=max_results, normalize=True, registry=registry)
    return result.results or []


def extract_page_foundation(url: str, timeout: int = 10):
    """Extract page text via Foundation WebExtraction. Returns WebExtractionResult."""
    from opc_foundation.web import WebExtractionRequest, extract_page
    req = WebExtractionRequest(url=url, timeout_seconds=timeout)
    return extract_page(req)
