"""
FastAPI Application Entry Point for Intent Operating Layer (IOL).
Configures middleware, routes, lifecycle handlers, and capability registrations.
"""

from contextlib import asynccontextmanager
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.iol.config import settings
from backend.iol.api.routes import api_router
from backend.iol.capabilities.registry import capability_registry
from backend.iol.adapters.outreach.adapter import register_outreach_capabilities
from backend.iol.capabilities.live_research import register_live_research_capabilities
from backend.iol.capabilities.educational import register_educational_capabilities
from backend.iol.capabilities.browser import register_browser_capabilities
from backend.iol.browser.session import browser_session_manager
from backend.iol.worker.background_worker import background_worker


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan startup and shutdown handler."""
    # 1. Register reusable capabilities
    register_outreach_capabilities(capability_registry)
    register_live_research_capabilities(capability_registry)
    register_educational_capabilities(capability_registry)
    register_browser_capabilities(capability_registry)

    # 2. Start independent background worker
    background_worker.start()

    yield

    # 3. Graceful shutdown
    await background_worker.stop()
    await browser_session_manager.close_all()


app = FastAPI(
    title="Intent Operating Layer (IOL)",
    description="General-purpose intent-to-outcome execution platform with reusable capability learning",
    version="0.5.0",
    lifespan=lifespan
)

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Intent Operating Layer",
        "version": "0.5.0-mvp",
        "capabilities_loaded": len(capability_registry.list_capabilities())
    }


@app.get("/healthz")
async def healthz():
    """Container liveness and readiness probe endpoint."""
    return {"status": "ok", "service": "iol-backend"}
