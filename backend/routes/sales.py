from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List

from backend.schemas.companyos import SalesBlock
from backend.services.execution.sales import get_email_provider

router = APIRouter(tags=["Sales"])

@router.post("/execute")
async def execute_sales_campaign(data: Dict[str, Any]):
    """
    Executes a sales campaign in the chosen mode (default: SANDBOX).
    Receives the entire SalesBlock output along with 'approvedProspectIds'.
    """
    # The frontend should pass `{ "salesBlock": {...}, "approvedProspectIds": ["...", "..."] }`
    sales_block = data.get("salesBlock", {})
    approved_ids = data.get("approvedProspectIds", [])
    
    execution_info = sales_block.get("execution", {})
    mode = (execution_info.get("mode", "SANDBOX") or "SANDBOX").upper()
    
    try:
        provider = get_email_provider(mode)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    outreach_list = sales_block.get("outreach", [])
    
    sent_count = 0
    errors = []
    compose_urls = []
    
    for draft in outreach_list:
        if draft.get("prospectId") in approved_ids:
            is_valid, msg = provider.validate_message(draft)
            if not is_valid:
                errors.append(f"Failed to validate {draft.get('prospectId')}: {msg}")
                continue
            
            try:
                result = provider.send_email(draft)
                draft["status"] = result.get("status", draft.get("status", "DRAFT"))
                draft["execution_result"] = result
                if result.get("composeUrl"):
                    compose_urls.append(result["composeUrl"])
                sent_count += 1
            except Exception as e:
                errors.append(f"Execution failed for {draft.get('prospectId')}: {str(e)}")
    
    if sent_count == 0 and errors:
        raise HTTPException(status_code=500, detail=f"Failed to send emails: {errors}")
        
    return {
        "status": "success", 
        "mode": mode,
        "sent_count": sent_count,
        "errors": errors,
        "outreach": outreach_list,
        "compose_urls": compose_urls,
        "open_in_browser": mode == "GMAIL_BROWSER"
    }
