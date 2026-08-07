import logging
from typing import Dict, Any

logger = logging.getLogger("companyos.agents.registry")

AGENT_REGISTRY = {
    "ceo": {
        "id": "ceo",
        "name": "CEO Orchestrator",
        "description": "Strategic vision, prioritization, overall plan coherence",
        "capabilities": ["planning", "synthesis"],
        "status": "idle"
    },
    "research": {
        "id": "research",
        "name": "Research Agent",
        "description": "Market analysis, competition, customer segmentation",
        "capabilities": ["market_research", "competitor_analysis"],
        "status": "idle"
    },
    "finance": {
        "id": "finance",
        "name": "Finance Agent",
        "description": "Capital requirements, revenue modeling, break-even analysis",
        "capabilities": ["financial_modeling", "budgeting"],
        "status": "idle"
    },
    "marketing": {
        "id": "marketing",
        "name": "Marketing Agent",
        "description": "Brand positioning, campaigns, digital channels",
        "capabilities": ["campaign_planning", "branding"],
        "status": "idle"
    },
    "sales": {
        "id": "sales",
        "name": "Sales Agent",
        "description": "Pricing, channels, go-to-market, targets",
        "capabilities": ["sales_strategy", "pricing"],
        "status": "idle"
    }
}

def get_agent_metadata(agent_id: str) -> Dict[str, Any]:
    return AGENT_REGISTRY.get(agent_id, None)
