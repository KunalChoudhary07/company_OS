"""
CompanyOS — Research Agent
===========================
Implements the Research Agent pipeline:

  CEO Task
    -> generate 3-5 search queries (deterministic, no LLM call)
    -> search_web() x N queries  (Tavily via web_search tool)
    -> deduplicate + filter results
    -> Groq analyzes all snippets at once  (1 LLM call)
    -> return structured ResearchResult

SSE events emitted:
  status  { agent: "research", status: "..." }
  search  { query: "...", count: N, results: [...] }
  result  { agent: "research", data: {...} }

API call budget per research run:
  - 3-5 Tavily searches
  - 1 Groq call (analysis)
  - Total: 4-6 API calls
"""

import asyncio
import json
import logging
from typing import AsyncGenerator, Dict, List, Any

from backend.services.tools.web_search import search_web, is_search_configured, SearchResponse
from backend.services.orchestrator import _call_llm

logger = logging.getLogger("companyos.agents.research")

# In-memory session cache: (company+objective) -> research result
# Prevents repeated API calls if same company is re-launched in the same session.
_research_cache: Dict[str, Dict] = {}

# ---- Prompt ----

RESEARCH_ANALYZER_PROMPT = """You are the Research Agent for CompanyOS. Your job is to analyze real web search results and produce a structured market research report.

IMPORTANT RULES:
- Do NOT invent facts. Base your analysis only on the provided search results.
- If the search results do not support a specific claim, say the information is insufficient.
- Separate observed facts (from sources) from your recommendations.
- Every competitor you mention should come from the search results if possible.
- Be specific about the company's industry and location.

You MUST output valid JSON ONLY matching this schema:

{
  "market_overview": "<2-3 sentences synthesizing market landscape from search results>",
  "market_size_tam": "<e.g. .5B or ₹450 Cr — from sources, or 'Insufficient data'>",
  "market_size_sam": "<e.g.  — from sources, or 'Insufficient data'>",
  "market_size_som": "<e.g.  — realistic SOM for this company>",
  "target_customers": [
    { "segment": "<segment name>", "description": "<description based on search results>", "priority": "primary" }
  ],
  "competitors": [
    { "name": "<competitor name from search>", "strength": "<key strength>", "weakness": "<key weakness>" }
  ],
  "market_opportunities": ["<opportunity 1 grounded in search results>", "<opportunity 2>", "<opportunity 3>"],
  "risks": ["<risk 1 from search context>", "<risk 2>", "<risk 3>"],
  "market_trends": ["<trend 1>", "<trend 2>", "<trend 3>"],
  "sources": [
    { "title": "<article title>", "url": "<actual URL from search>", "domain": "<domain>" }
  ],
  "search_queries_used": ["<query 1>", "<query 2>"]
}
"""


def _generate_search_queries(req) -> List[str]:
    """
    Deterministically generate 4-5 targeted search queries from company profile.
    No LLM call needed — saves API quota and latency.
    """
    name = req.company.name
    industry = req.company.industry
    city = req.company.city
    country = req.company.country
    customers = req.business.target_customers[:80]  # truncate
    stage = req.company.stage

    queries = [
        f"{industry} market {country} 2025 2026",
        f"{industry} startups {country} competitors funding",
        f"{industry} {city} market opportunities",
        f"{industry} target customers {customers[:40]} trends",
        f"{name} {industry} {country} pricing market size",
    ]

    # Deduplicate and return max 5
    seen = set()
    unique = []
    for q in queries:
        q_norm = q.strip().lower()
        if q_norm not in seen:
            seen.add(q_norm)
            unique.append(q.strip())
    return unique[:5]


def _build_analysis_prompt(req, all_results: List[Dict], queries: List[str]) -> str:
    """
    Build the Groq analysis prompt from the company profile + search results.
    Keeps context compact: max 300 chars per snippet.
    """
    company_context = f"""Company: {req.company.name}
Industry: {req.company.industry}
Location: {req.company.city}, {req.company.country}
Stage: {req.company.stage}
Target Customers: {req.business.target_customers}
Business Model: {req.business.business_model}
Problem: {req.business.problem}
Solution: {req.business.solution}
Budget: {req.finance.budget}
Objective: {req.objective}"""

    # Compact snippets — never send huge raw pages to Groq
    snippets_text = ""
    for i, r in enumerate(all_results[:30], 1):  # hard cap at 30 results
        snippet = r.get("snippet", "")[:300]  # 300 chars max per result
        snippets_text += f"\n[{i}] {r.get('title', '')} ({r.get('source', '')})\n{snippet}\nURL: {r.get('url', '')}\n"

    return f"""COMPANY PROFILE:
{company_context}

SEARCH QUERIES USED:
{chr(10).join(f'- {q}' for q in queries)}

WEB SEARCH RESULTS ({len(all_results)} sources):
{snippets_text}

Analyze these search results for the company above. Produce the structured JSON research report."""


async def run_research_agent(
    req,
    emit_status,
    emit_search,
) -> Dict[str, Any]:
    """
    Core Research Agent logic.

    Args:
        req: InitiativeRequest from the CEO dispatcher
        emit_status: async callable(status_text) to send status SSE
        emit_search: async callable(query, count, results) to send search SSE

    Returns:
        Structured research result dict (matching ResearchBlock schema)
    """
    company_key = f"{req.company.name}|{req.objective}"

    # Session cache check
    if company_key in _research_cache:
        logger.info(f"Research cache hit for: {req.company.name}")
        await emit_status("Loaded from session cache ✓")
        return _research_cache[company_key]

    if not is_search_configured():
        raise RuntimeError(
            "TAVILY_API_KEY is not set. Add it to your .env file. "
            "Get a free key at https://tavily.com"
        )

    # 1. Generate search queries
    await emit_status("🔎 Understanding research task...")
    queries = _generate_search_queries(req)
    logger.info(f"Research queries for {req.company.name}: {queries}")

    # 2. Execute searches (sequentially to be polite to the API)
    all_results: List[Dict] = []
    seen_urls: set = set()

    for query in queries:
        await emit_status(f"🔎 Searching: {query}")
        try:
            response: SearchResponse = await search_web(query)
        except RuntimeError as e:
            raise  # Re-raise key missing error — do not swallow
        except Exception as e:
            logger.warning(f"Search failed for '{query}': {e}")
            await emit_search(query, 0, [], error=str(e))
            continue

        # Deduplicate across queries
        fresh_results = []
        for r in response.results:
            if r.url not in seen_urls:
                seen_urls.add(r.url)
                fresh_results.append(r.to_dict())

        all_results.extend(fresh_results)
        await emit_search(query, len(fresh_results), fresh_results)

        # Small delay to be polite to the API
        await asyncio.sleep(0.3)

    if not all_results:
        raise RuntimeError("No search results returned. Check TAVILY_API_KEY or network.")

    total = len(all_results)
    await emit_status(f"🧠 Analyzing {total} sources...")
    logger.info(f"Research: {total} unique results collected for {req.company.name}")

    # 3. Groq analysis — ONE call with all snippets
    analysis_prompt = _build_analysis_prompt(req, all_results, queries)
    raw = await _call_llm(RESEARCH_ANALYZER_PROMPT, analysis_prompt)

    # Parse JSON response
    cleaned = raw.strip()
    if cleaned.startswith("`"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1]) if lines[-1].strip() == "`" else "\n".join(lines[1:])
    result = json.loads(cleaned)

    # Ensure required fields exist (fallbacks so the schema validator doesn't crash)
    result.setdefault("market_overview", "")
    result.setdefault("market_size_tam", "Insufficient data")
    result.setdefault("market_size_sam", "Insufficient data")
    result.setdefault("market_size_som", "Insufficient data")
    result.setdefault("target_customers", [])
    result.setdefault("competitors", [])
    result.setdefault("market_opportunities", [])
    result.setdefault("risks", [])
    result.setdefault("market_trends", [])
    result.setdefault("sources", [])
    result.setdefault("search_queries_used", queries)

    # Cache for this session
    _research_cache[company_key] = result
    logger.info(f"Research complete for {req.company.name}")
    return result
