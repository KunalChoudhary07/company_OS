import asyncio
import json

async def test_execute():
    from backend.schemas.companyos import MarketingBlock
    
    # Just load a dummy payload
    payload = {
        "agent": "marketing",
        "status": "COMPLETED",
        "campaign": {
            "name": "NovaMind Launch",
            "objective": "Lead Generation",
            "recommendedBudget": 15000,
            "durationDays": 14,
            "dailyBudget": 1071,
            "channels": ["Instagram", "Facebook"],
            "targetAudience": {
                "demographics": "College students",
                "geography": "Chandigarh",
                "interests": ["AI", "Education"],
                "pain_points": ["Note taking is hard"]
            },
            "kpis": ["Leads"]
        },
        "strategy": {
            "positioning": "AI Study",
            "valueProposition": "Smart",
            "messaging": "Work smart",
            "reasoning": "Fits target"
        },
        "adCopy": {
            "headlines": ["1", "2", "3"],
            "primaryTexts": ["1", "2", "3"],
            "ctas": ["1", "2", "3"]
        },
        "creativeConcepts": [],
        "adSets": [],
        "recommendations": [],
        "risks": [],
        "execution": {
            "mode": "SANDBOX",
            "status": "READY_FOR_APPROVAL"
        }
    }
    
    # Validate payload through schema
    try:
        block = MarketingBlock(**payload)
        print("Schema validation successful")
    except Exception as e:
        print("Schema validation failed:", e)
        return

    # Call execution provider
    from backend.services.execution.marketing import get_campaign_provider
    provider = get_campaign_provider("SANDBOX")
    
    valid, msg = provider.validate_campaign(payload)
    print("Validation:", valid, msg)
    
    if valid:
        result = provider.create_campaign(payload)
        print("Execution result:", result)

if __name__ == "__main__":
    asyncio.run(test_execute())
