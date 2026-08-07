from fastapi import APIRouter

router = APIRouter(tags=["Chat"])


@router.post("/chat")
async def chat(data: dict):
    """Placeholder chat endpoint for future conversational AI features."""
    return {"reply": "Chat feature coming soon.", "status": "ok"}
