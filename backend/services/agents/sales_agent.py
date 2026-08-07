import asyncio
import json
import logging
import uuid
import re
from typing import Any, Callable, Dict, List, Optional

import httpx

from backend.schemas.companyos import InitiativeRequest, SalesBlock, SalesICP, Prospect
from backend.prompts.agents import SALES_AGENT_PROMPT
from backend.services.orchestrator import _call_llm
from backend.services.task_dispatcher import parse_json_from_llm
from backend.services.tools.web_search import search_web, is_search_configured

logger = logging.getLogger(__name__)

# Generic email regex — matches any local-part@domain.tld pattern.
EMAIL_REGEX = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

# Emails that show up on nearly every website but are useless for outreach
# (privacy policy examples, image placeholders, tracking pixels, etc.)
EMAIL_BLOCKLIST_SUBSTRINGS = (
    "example.com", "sentry.io", "wixpress.com", "godaddy.com",
    "yourdomain.com", "domain.com", "email.com", ".png", ".jpg", ".gif",
)

CONTACT_PATHS = ("", "/contact", "/contact-us", "/about", "/about-us")


def _is_useful_email(email: str) -> bool:
    email = email.lower()
    return not any(bad in email for bad in EMAIL_BLOCKLIST_SUBSTRINGS)


async def _fetch_emails_from_page(client: httpx.AsyncClient, url: str) -> List[str]:
    """Fetch a single page and extract candidate emails (mailto: links + raw text matches)."""
    try:
        resp = await client.get(url, timeout=6.0, follow_redirects=True)
        if resp.status_code >= 400:
            return []
        html = resp.text
    except Exception:
        return []

    found = set()

    # 1. mailto: links — highest confidence, these are explicitly published contact emails
    for m in re.findall(r'mailto:([^"\'\s?<>]+)', html, re.IGNORECASE):
        addr = m.strip()
        if EMAIL_REGEX.fullmatch(addr) and _is_useful_email(addr):
            found.add(addr.lower())

    # 2. Any plain email text on the page (lower confidence, but still useful)
    for m in EMAIL_REGEX.findall(html):
        if _is_useful_email(m):
            found.add(m.lower())

    return list(found)


async def discover_email_from_website(domain: str) -> Optional[str]:
    """
    Try to find a real, published contact email for a company by fetching its
    homepage and a few common contact pages. Returns the best candidate email
    or None if nothing usable was found.
    """
    base = domain if domain.startswith("http") else f"https://{domain}"
    async with httpx.AsyncClient(headers={"User-Agent": "Mozilla/5.0 (CompanyOS SalesAgent)"}) as client:
        for path in CONTACT_PATHS:
            emails = await _fetch_emails_from_page(client, base.rstrip("/") + path)
            if emails:
                # Prefer generic business addresses over random personal-looking ones
                priority = ["contact", "info", "sales", "hello", "support", "business"]
                emails.sort(key=lambda e: next((i for i, p in enumerate(priority) if p in e), len(priority)))
                return emails[0]
    return None

def generate_icp(req: InitiativeRequest) -> SalesICP:
    """Generate a dynamic ICP based on the company's profile."""
    # Basic rule-based dynamic ICP generation
    industry = req.company.industry or "Technology"
    location = req.company.city or req.company.country or "Global"
    
    target = req.business.target_customers.lower() if req.business.target_customers else ""
    
    # Simple keyword mapping for company size
    company_size = "50-500"
    if "enterprise" in target or "large" in target:
        company_size = "1000+"
    elif "startup" in target or "small" in target:
        company_size = "1-50"
    
    pain_points = [
        f"Looking for solutions related to {req.business.problem}",
        "Seeking efficiency and cost reduction"
    ]
    
    buying_signals = [
        "Hiring new roles",
        "Digital transformation initiatives",
        "Recent expansion or growth"
    ]
    
    return SalesICP(
        industry=industry,
        location=location,
        companySize=company_size,
        painPoints=pain_points,
        buyingSignals=buying_signals
    )

def extract_email(text: str) -> str | None:
    """Attempt to find a business email in a short snippet of text (e.g. search result)."""
    match = EMAIL_REGEX.search(text.lower())
    if match and _is_useful_email(match.group(0)):
        return match.group(0)
    return None

def score_prospect(p: Prospect, icp: SalesICP, target_audience: str) -> None:
    """Deterministically score a prospect out of 100 based on ICP match."""
    score = 0
    bd = p.scoreBreakdown
    
    desc = p.description.lower()
    
    # Industry Fit (0-30)
    if icp.industry.lower() in p.industry.lower() or icp.industry.lower() in desc:
        bd.industryFit = 30
    elif any(word in desc for word in icp.industry.lower().split()):
        bd.industryFit = 15
    else:
        bd.industryFit = 5
        
    # Location Fit (0-20)
    if icp.location.lower() in p.location.lower() or icp.location.lower() in desc:
        bd.locationFit = 20
    else:
        bd.locationFit = 5
        
    # Company Fit (0-20)
    target_words = [w for w in target_audience.lower().split() if len(w) > 3]
    matches = sum(1 for w in target_words if w in desc)
    bd.companyFit = min(20, matches * 5)
    
    # Pain Point Fit (0-15)
    # Generic assumption: if they are in the target audience, they have the pain point
    if bd.companyFit > 10:
        bd.painPointFit = 15
    else:
        bd.painPointFit = 5
        
    # Buying Signals (0-15)
    if "hire" in desc or "grow" in desc or "expand" in desc or "new" in desc:
        bd.buyingSignals = 15
    else:
        bd.buyingSignals = 0
        
    p.score = bd.industryFit + bd.locationFit + bd.companyFit + bd.painPointFit + bd.buyingSignals
    
    if p.score > 80:
        p.reason = "Strong industry match and clear alignment with the target customer."
    elif p.score > 60:
        p.reason = "Moderate fit based on industry and location."
    else:
        p.reason = "Low fit, lacks strong signals."


async def run_sales_agent(
    req: InitiativeRequest,
    results: Dict[str, Any],
    emit: Callable[[str], Any]
) -> dict:
    """Run the complete sales prospecting and outreach pipeline."""
    
    await emit("Understanding ideal customer...")
    icp = generate_icp(req)
    
    if not is_search_configured():
        raise ValueError("Sales Agent requires search capabilities to find prospects.")

    await emit("Searching potential customers...")
    
    # Generate 3 targeted queries based on ICP
    queries = [
        f"{icp.industry} companies {icp.location}",
        f"{req.business.target_customers} organizations {icp.location}",
        f"{icp.industry} businesses looking for {req.business.solution.split()[0]} {icp.location}"
    ]
    
    all_results = []
    for q in queries:
        try:
            resp = await search_web(q)
            if resp.results:
                all_results.extend(resp.results)
        except Exception as e:
            logger.error(f"Search failed for query '{q}': {e}")
            
    if not all_results:
        raise ValueError("No suitable prospects found. Search returned empty.")

    await emit("Evaluating prospects...")
    
    # Normalize and deduplicate
    seen_domains = set()
    prospects = []
    
    for r in all_results:
        url = r.url
        # extract rough domain
        domain_match = re.search(r'https?://(?:www\.)?([^/]+)', url)
        if not domain_match: continue
        domain = domain_match.group(1).lower()
        
        # Skip obvious non-business pages
        if any(x in domain for x in ['linkedin', 'facebook', 'twitter', 'instagram', 'yelp', 'yellowpages', 'glassdoor']):
            continue
            
        if domain in seen_domains:
            continue
            
        seen_domains.add(domain)
        
        # We assume the title is the company name for now (often true for homepages)
        company_name = r.title.split('-')[0].split('|')[0].strip()
        
        # Extract email from the search snippet (cheap, no network call)
        email = extract_email(r.snippet)
        
        # Create prospect
        p = Prospect(
            id=f"prospect-{uuid.uuid4().hex[:8]}",
            companyName=company_name,
            website=domain,
            industry=icp.industry,
            location=icp.location,
            description=r.snippet[:500],  # truncate description
            score=0,
            scoreBreakdown={},
            reason="",
            sourceUrls=[url],
            publicEmail=email,
            emailSource="search_snippet" if email else None
        )
        prospects.append(p)
        
        if len(prospects) >= 20: # hard limit for hackathon
            break

    if not prospects:
        raise ValueError("No suitable prospects found after filtering.")

    await emit("Scoring prospects...")
    
    for p in prospects:
        score_prospect(p, icp, req.business.target_customers)
        
    # Rank prospects
    prospects.sort(key=lambda x: x.score, reverse=True)
    
    # Take top 10
    top_prospects = prospects[:10]

    # For top prospects without an email from the search snippet, try to find
    # a real published contact email by fetching their website directly.
    # This is far more reliable than scanning short search snippets, since most
    # businesses publish their email on a homepage/contact page, not in a
    # search engine's meta description.
    await emit("Looking up company contact emails...")
    scrape_targets = [p for p in top_prospects if not p.publicEmail]
    if scrape_targets:
        scrape_results = await asyncio.gather(
            *[discover_email_from_website(p.website) for p in scrape_targets],
            return_exceptions=True
        )
        for p, found_email in zip(scrape_targets, scrape_results):
            if isinstance(found_email, Exception):
                logger.warning(f"Email scrape failed for {p.website}: {found_email}")
                continue
            if found_email:
                p.publicEmail = found_email
                p.emailSource = "website_scrape"

    await emit("Generating personalized outreach...")
    
    # Build prompt for Groq to write the emails
    marketing_ctx = results.get("marketing", {})
    marketing_val_prop = marketing_ctx.get("strategy", {}).get("valueProposition", req.business.solution)
    
    prospects_json = json.dumps([
        {
            "id": p.id,
            "companyName": p.companyName,
            "description": p.description,
            "publicEmail": p.publicEmail
        } for p in top_prospects
    ])
    
    user_prompt = f"""
COMPANY PROFILE
Name: {req.company.name}
Solution: {req.business.solution}
Marketing Value Proposition: {marketing_val_prop}

ICP: {icp.model_dump_json()}

PROSPECTS:
{prospects_json}

Write the outreach emails as per the instructions in the system prompt.
"""
    
    raw_response = await _call_llm(SALES_AGENT_PROMPT, user_prompt)
    parsed = await parse_json_from_llm(raw_response)
    
    # Merge outreach drafts
    outreach_list = parsed.get("outreach", [])
    
    # Ensure NO_EMAIL logic is strictly enforced if LLM messed up
    for out in outreach_list:
        if not out.get("email") or str(out.get("email")).lower() == "null":
            out["email"] = None
            out["status"] = "NO_EMAIL"
        else:
            out["status"] = "DRAFT"
            
    await emit("Waiting for approval")
    
    block = SalesBlock(
        icp=icp,
        prospects=top_prospects,
        outreach=outreach_list
    )
    
    return block.model_dump()
