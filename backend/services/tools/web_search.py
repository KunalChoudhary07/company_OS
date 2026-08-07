"""
CompanyOS — Web Search Tool
============================
Single-responsibility abstraction over a search API.

Provider: Tavily (https://tavily.com)
  - Free tier: 1,000 searches/month
  - No SDK required — pure httpx (already a project dependency)
  - Purpose-built for AI agents — returns clean snippets

Usage:
    from backend.services.tools.web_search import search_web
    results = await search_web("EdTech market India 2025")

Replace Tavily with any other provider by updating _call_tavily only.
The Research Agent never touches provider-specific code.
"""

import logging
import os
from typing import List, Optional

import httpx

logger = logging.getLogger("companyos.tools.web_search")

# --- Configuration ---
TAVILY_BASE_URL = "https://api.tavily.com/search"
MAX_RESULTS_PER_QUERY = 8
REQUEST_TIMEOUT = 15


class SearchResult:
    def __init__(self, title: str, url: str, snippet: str, source: str):
        self.title = title
        self.url = url
        self.snippet = snippet
        self.source = source

    def to_dict(self) -> dict:
        return {"title": self.title, "url": self.url, "snippet": self.snippet, "source": self.source}


class SearchResponse:
    def __init__(self, query: str, results: List[SearchResult], error: Optional[str] = None):
        self.query = query
        self.results = results
        self.error = error

    @property
    def count(self) -> int:
        return len(self.results)

    def to_dict(self) -> dict:
        return {"query": self.query, "count": self.count, "results": [r.to_dict() for r in self.results], "error": self.error}


async def _call_tavily(query: str, max_results: int) -> SearchResponse:
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
    if not TAVILY_API_KEY:
        raise RuntimeError(
            "TAVILY_API_KEY is not set. Add it to your .env file. "
            "Get a free key at https://tavily.com"
        )
    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "search_depth": "basic",
        "include_answer": False,
        "include_raw_content": False,
        "max_results": max_results,
    }
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.post(TAVILY_BASE_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except httpx.TimeoutException:
        logger.error(f"Tavily timeout for query: {query[:60]}")
        return SearchResponse(query=query, results=[], error="Search timed out")
    except httpx.HTTPStatusError as e:
        logger.error(f"Tavily HTTP {e.response.status_code} for query: {query[:60]}")
        return SearchResponse(query=query, results=[], error=f"Search API error: {e.response.status_code}")
    except Exception as e:
        logger.error(f"Tavily unexpected error: {e}")
        return SearchResponse(query=query, results=[], error=str(e))

    normalized: List[SearchResult] = []
    seen_urls = set()
    for item in data.get("results", []):
        url = item.get("url", "")
        if url in seen_urls:
            continue
        seen_urls.add(url)
        domain = _extract_domain(url)
        normalized.append(SearchResult(
            title=item.get("title", ""),
            url=url,
            snippet=item.get("content", ""),
            source=domain,
        ))

    logger.info(f"Tavily: '{query[:60]}' -> {len(normalized)} results")
    return SearchResponse(query=query, results=normalized)


async def search_web(query: str, max_results: int = MAX_RESULTS_PER_QUERY) -> SearchResponse:
    max_results = min(max_results, 10)
    return await _call_tavily(query, max_results)


def is_search_configured() -> bool:
    return bool(os.getenv("TAVILY_API_KEY", ""))


def _extract_domain(url: str) -> str:
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return url
