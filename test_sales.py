import asyncio
import json
from dotenv import load_dotenv
load_dotenv()
from backend.schemas.companyos import InitiativeRequest, CompanyProfileInput, BusinessProfileInput
from backend.services.agents.sales_agent import run_sales_agent

async def test():
    req = InitiativeRequest(
        company=CompanyProfileInput(
            name="NovaMind",
            industry="EdTech",
            city="Chandigarh",
            country="India",
            stage="Seed",
        ),
        business=BusinessProfileInput(
            problem="Students struggling to take notes and retain complex information",
            solution="AI-powered study notes and quiz generator",
            target_customers="College students and small private colleges",
            business_model="B2C SaaS",
            description="An AI study companion"
        ),
        goals={"primary_goal": "Get users", "short_term": "Launch", "long_term": "Scale"},
        finance={"budget": "1000", "expected_revenue": "0", "monthly_budget": "500", "funding_status": "Bootstrapped"},
        team={"size": "1", "founder_role": "CEO", "skills": "Tech", "departments": []},
        objective="Find 10 early beta testers."
    )
    
    # Mock some basic marketing results
    mock_results = {
        "marketing": {
            "strategy": {
                "valueProposition": "Instant AI clarity for complex coursework."
            }
        }
    }
    
    async def emit_status(text):
        print(f"STATUS: {text}")
        
    print("Running sales agent...")
    try:
        res = await run_sales_agent(req, mock_results, emit_status)
        print("=== RESULT ===")
        print(json.dumps(res, indent=2))
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(test())
