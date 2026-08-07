import json
import logging
from typing import Any, Callable, Dict, Optional
from backend.schemas.companyos import InitiativeRequest, MarketingBlock
from backend.prompts.agents import MARKETING_AGENT_PROMPT
from backend.services.orchestrator import _call_llm
from backend.services.task_dispatcher import parse_json_from_llm

logger = logging.getLogger(__name__)

async def run_marketing_agent(
    req: InitiativeRequest,
    results: Dict[str, Any],
    emit: Callable[[str], Any]
) -> dict:
    """
    Run the marketing agent to generate a campaign plan and return a structured dictionary.
    """
    await emit("Loading Research and Finance context...")

    # Build context from previous agents if available
    research_ctx = "Research context unavailable. Audience recommendation is based on company profile."
    if "research" in results and results["research"]:
        r = results["research"]
        research_ctx = f"""
Summary: {r.get('market_overview', '')}
Target Customers: {r.get('target_customers', [])}
Competitors: {r.get('competitors', [])}
Opportunities: {r.get('opportunities', [])}
"""

    finance_ctx = "No financial dataset available. Budget recommendation is based on founder-provided budget."
    if "finance" in results and results["finance"]:
        f = results["finance"]
        metrics = f.get("metrics", {})
        finance_ctx = f"""
Total Revenue: {metrics.get('totalRevenue')}
Total Expenses: {metrics.get('totalExpenses')}
Marketing Spend: {metrics.get('marketingSpend')}
Profit Margin: {metrics.get('profitMargin')}
Recommendations from Finance: {f.get('aiInsights', {}).get('recommendations', [])}
"""

    user_prompt = f"""
COMPANY PROFILE
Name: {req.company.name}
Industry: {req.company.industry}
Location: {req.company.city}, {req.company.country}
Objective: {req.objective}
Budget Constraint (from founder): {req.finance.budget}
Target Customers: {req.business.target_customers}
Problem: {req.business.problem}
Solution: {req.business.solution}

RESEARCH CONTEXT
{research_ctx}

FINANCE CONTEXT
{finance_ctx}

Generate a comprehensive marketing campaign plan structured as JSON.
"""
    await emit("Building campaign strategy...")
    
    try:
        raw_response = await _call_llm(MARKETING_AGENT_PROMPT, user_prompt)
        parsed = await parse_json_from_llm(raw_response)
        
        await emit("Campaign strategy generated")
        await emit("Ad copy generated")
        
        # Validation checks
        campaign = parsed.get("campaign", {})
        if not campaign.get("name") or not campaign.get("objective") or campaign.get("recommendedBudget", 0) <= 0 or not campaign.get("channels") or not parsed.get("adCopy", {}).get("headlines"):
            raise ValueError("Campaign validation failed: missing essential fields.")
        
        await emit("Campaign validated")
        await emit("Waiting for founder approval")

        # Create the model to validate types/defaults and export back to dict
        block = MarketingBlock(**parsed)
        return block.model_dump()
        
    except Exception as e:
        logger.error(f"Marketing Agent failed: {e}")
        raise ValueError(f"Marketing strategy generation failed. Error: {str(e)}")
