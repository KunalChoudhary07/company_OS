"""
CompanyOS — FastAPI Application Entry Point
"""

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.responses import Response

# Load .env before anything else
load_dotenv()

from backend.models.db import init_db
from backend.routes.chat import router as chat_router
from backend.routes.initiative import router as initiative_router
from backend.routes.marketing import router as marketing_router
from backend.routes.sales import router as sales_router

# ─── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("companyos")


# ─── Lifespan ────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("CompanyOS starting up...")
    init_db()
    logger.info("SQLite database initialized")
    from backend.services.orchestrator import DEMO_MODE, LLM_PROVIDER
    logger.info(f"Mode: {'DEMO' if DEMO_MODE else 'LIVE'} | Provider: {LLM_PROVIDER}")
    yield
    logger.info("CompanyOS shutting down")


# ─── App ─────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="CompanyOS API",
    description="AI Operating System — Single-call orchestration backend",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS — allow browser requests from any localhost port during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "null",  # file:// origin
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
# NOTE: initiative_router already declares prefix="/api" internally, so it is
# mounted with no additional prefix here to avoid a double "/api/api/..." path.
app.include_router(initiative_router)
app.include_router(chat_router, prefix="/api")
app.include_router(marketing_router, prefix="/api/marketing")
app.include_router(sales_router, prefix="/api/sales")

# Serve the frontend index.html at root
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..")

@app.get("/", include_in_schema=False)
async def serve_frontend():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    return FileResponse(index_path, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

# Serve any other static assets (if needed in the future)
@app.get("/{path:path}", include_in_schema=False)
async def catch_all(path: str):
    """Serve index.html for all non-API routes (SPA fallback)."""
    if path.startswith("api/"):
        from fastapi import HTTPException
        raise HTTPException(status_code=404)
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    return FileResponse(index_path, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
