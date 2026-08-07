import asyncio
import json
from dotenv import load_dotenv

load_dotenv()

async def test():
    from backend.schemas.companyos import InitiativeRequest, CompanyProfileInput, BusinessProfileInput, GoalsProfileInput, FinanceProfileInput, TeamProfileInput
    from backend.services.agents.marketing_agent import run_marketing_agent

    req = InitiativeRequest(
        company=CompanyProfileInput(name="NovaMind", industry="EdTech", stage="Seed", country="India", city="Chandigarh"),
        business=BusinessProfileInput(description="AI Study Platform", business_model="B2C", target_customers="College Students", problem="Hard to study", solution="AI Notes"),
        goals=GoalsProfileInput(primary_goal="Launch", short_term="MVP", long_term="Scale"),
        finance=FinanceProfileInput(budget="Rs 10,00,000", expected_revenue="Rs 5,00,000", monthly_budget="Rs 1,00,000", funding_status="Bootstrapped"),
        team=TeamProfileInput(size="1", founder_role="CEO", skills="Tech", departments=["Eng"]),
        objective="Launch AI app for students"
    )
    
    results = {}
    async def emit_status(s):
        print(f"STATUS: {s}")
    
    try:
        result = await run_marketing_agent(req, results, emit_status)
        print("\n=== RESULT ===")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print("FAILED:", e)

if __name__ == "__main__":
    asyncio.run(test())
