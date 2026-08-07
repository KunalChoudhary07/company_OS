import asyncio
import json
from backend.schemas.companyos import InitiativeRequest, CompanyProfileInput, BusinessProfileInput, GoalsProfileInput, FinanceProfileInput, TeamProfileInput

async def test():
    req = InitiativeRequest(
        company=CompanyProfileInput(name="Test", industry="Tech", stage="Seed", country="USA", city="SF"),
        business=BusinessProfileInput(description="D", business_model="B", target_customers="T", problem="P", solution="S"),
        goals=GoalsProfileInput(primary_goal="G", short_term="S", long_term="L"),
        finance=FinanceProfileInput(budget="1", expected_revenue="1", monthly_budget="1", funding_status="1"),
        team=TeamProfileInput(size="1", founder_role="1", skills="1", departments=["1"]),
        objective="Testing"
    )
    with open("test_finance.csv") as f:
        csv_data = f.read()

    from backend.services.agents.finance_agent import run_finance_agent
    async def emit_status(s):
        print(f"STATUS: {s}")
    
    result = await run_finance_agent(req, csv_data, emit_status)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(test())
