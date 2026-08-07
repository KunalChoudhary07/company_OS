from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from backend.schemas.companyos import MarketingBlock
from backend.services.execution.marketing import get_campaign_provider

router = APIRouter(tags=["Marketing"])

@router.post("/execute")
async def execute_marketing_campaign(data: Dict[str, Any]):
    """
    Executes a marketing campaign in the chosen mode.

    Expected payload shape:
      {
        ...MarketingBlock fields (campaign, strategy, adCopy, execution, ...),
        "metaCredentials": { "accessToken": "...", "adAccountId": "..." }  # only for META_LIVE
      }

    Modes:
      - SANDBOX (default): simulated execution, no external calls, no cost.
      - META_LIVE: creates a real Campaign + Ad Set on Meta (Facebook/Instagram)
        Marketing API. Always created in PAUSED status — nothing spends money
        until the founder reviews and manually activates it in Ads Manager.
        Requires the user's own Meta access token + ad account id, supplied
        per-request. Credentials are never persisted server-side.
    """
    execution_info = data.get("execution", {})
    mode = execution_info.get("mode", "SANDBOX")
    credentials = data.get("metaCredentials")

    try:
        provider = get_campaign_provider(mode, credentials)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    is_valid, msg = provider.validate_campaign(data)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Campaign validation failed: {msg}")

    # Execute the campaign
    try:
        execution_result = await provider.create_campaign(data)
        return {"status": "success", "execution": execution_result}
    except RuntimeError as e:
        # Errors surfaced from the Meta Graph API (bad token, permissions, etc.)
        raise HTTPException(status_code=502, detail=f"Meta API rejected the request: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Campaign execution failed: {str(e)}")
