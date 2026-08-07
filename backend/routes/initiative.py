import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.models.db import get_db, Initiative
from backend.schemas.companyos import InitiativeRequest, FollowUpRequest, FollowUpResponse
from backend.services import cache, orchestrator
from backend.services.task_dispatcher import TaskDispatcher
import json
import asyncio

logger = logging.getLogger("companyos.routes")
router = APIRouter(prefix="/api", tags=["CompanyOS"])


@router.post("/initiative")
async def create_initiative(
    req: InitiativeRequest,
    db: Session = Depends(get_db),
):
    """
    Main endpoint. ONE LLM call per unique initiative (cached thereafter).
    Returns the full CompanyOS structured response.
    """
    logger.info(f"[CompanyOS Backend] Request received")
    logger.info(f"[CompanyOS Backend] Company: {req.company.name}")
    logger.info(f"[CompanyOS Backend] Industry: {req.company.industry}")
    logger.info(f"[CompanyOS Backend] Objective: {req.objective[:120]}")

    async def event_generator():
        # Check cache first
        cache_key = f"{req.company.name} - {req.objective}"
        cached_data, cached_id = cache.get_cached(db, cache_key)
        if cached_data:
            logger.info("Returning cached result via SSE")
            yield f"event: complete\ndata: {json.dumps({'id': cached_id, 'cached': True, 'final_data': cached_data})}\n\n"
            return

        dispatcher = TaskDispatcher(req)
        
        try:
            async for event in dispatcher.run():
                if event.startswith("event: complete"):
                    data_part = event.split("data: ")[1].strip()
                    payload = json.loads(data_part)
                    final_data = payload.get("final_data")
                    if final_data:
                        initiative_id = cache.store_result(db, cache_key, final_data)
                        payload["id"] = initiative_id
                        payload["cached"] = False
                        yield f"event: complete\ndata: {json.dumps(payload)}\n\n"
                else:
                    yield event
                    
        except Exception as e:
            logger.error(f"Orchestrator error: {e}")
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.post("/finance/analyze")
async def analyze_finance(req: InitiativeRequest):
    """
    Independent endpoint to run the Finance Agent with CSV data.
    Streams SSE events back to the UI.
    """
    logger.info(f"[CompanyOS Backend] Finance analysis requested for: {req.company.name}")
    
    async def event_generator():
        try:
            from backend.services.agents.finance_agent import run_finance_agent
            finance_queue: asyncio.Queue = asyncio.Queue()

            async def _emit_finance_status(text: str):
                await finance_queue.put(f"event: status\ndata: {json.dumps({'agent': 'finance', 'status': text})}\n\n")

            async def _run_finance():
                try:
                    if not req.csv_data:
                        await finance_queue.put(("DONE", {
                            "agent": "finance",
                            "status": "COMPLETED",
                            "metrics": {},
                            "aiInsights": {"summary": "Financial dataset not available."},
                            "dataQuality": {"rows": 0, "validRows": 0, "invalidRows": 0, "missingColumns": []},
                            "forecast": {"available": False, "nextMonthRevenue": None, "nextThreeMonths": []}
                        }))
                        return

                    result = await run_finance_agent(req, req.csv_data, _emit_finance_status)
                    await finance_queue.put(("DONE", result))
                except Exception as e:
                    await finance_queue.put(("ERROR", str(e)))

            finance_task = asyncio.create_task(_run_finance())

            while True:
                item = await finance_queue.get()
                if isinstance(item, str):
                    yield item
                elif isinstance(item, tuple):
                    status, payload = item
                    if status == "DONE":
                        yield f"event: complete\ndata: {json.dumps({'final_data': {'finance': payload}})}\n\n"
                        break
                    else:
                        logger.error(f"Finance Agent error: {payload}")
                        yield f"event: status\ndata: {json.dumps({'agent': 'finance', 'status': 'FAILED ✗'})}\n\n"
                        yield f"event: error\ndata: {json.dumps({'message': f'Finance Agent validation failed: {payload}'})}\n\n"
                        return
        except Exception as e:
            logger.error(f"Finance Agent fatal: {e}")
            yield f"event: status\ndata: {json.dumps({'agent': 'finance', 'status': 'FAILED ✗'})}\n\n"
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/initiative/{initiative_id}")
async def get_initiative(initiative_id: str, db: Session = Depends(get_db)):
    """Retrieve a previously generated initiative by ID."""
    data = cache.get_by_id(db, initiative_id)
    if not data:
        raise HTTPException(status_code=404, detail="Initiative not found")
    return {"id": initiative_id, "data": data}


@router.get("/initiatives")
async def list_initiatives(db: Session = Depends(get_db)):
    """List all stored initiatives (summary only)."""
    return cache.list_all(db)


@router.post("/followup", response_model=FollowUpResponse)
async def followup(req: FollowUpRequest, db: Session = Depends(get_db)):
    """
    Answer a follow-up question using stored context.
    One small LLM call — does NOT regenerate the full plan.
    """
    logger.info(f"POST /api/followup — question: {req.question[:80]}")

    initiative_data = cache.get_by_id(db, req.initiative_id)
    if not initiative_data:
        raise HTTPException(status_code=404, detail="Initiative not found. Please generate an initiative first.")

    answer = await orchestrator.run_followup(req.question, initiative_data)
    return FollowUpResponse(answer=answer, initiative_id=req.initiative_id)


@router.delete("/session")
async def clear_session(db: Session = Depends(get_db)):
    """
    Clear all stored initiatives from the database.
    Called on logout/reset to remove all company data.
    """
    try:
        deleted = db.query(Initiative).delete()
        db.commit()
        logger.info(f"Session cleared — deleted {deleted} initiatives")
        return {"status": "cleared", "deleted": deleted}
    except Exception as e:
        logger.error(f"Session clear error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear session: {str(e)}")


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "demo_mode": orchestrator.DEMO_MODE,
        "llm_provider": orchestrator.LLM_PROVIDER,
    }
