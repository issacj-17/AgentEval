"""FastAPI application for AgentEval.

Multi-agent AI evaluation platform with health checks, campaign management,
and comprehensive observability.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agenteval.api.routes import admin, campaigns, health, results
from agenteval.config import settings

app = FastAPI(
    title="AgentEval API",
    version="1.0.0",
    description="Multi-Agent AI Evaluation Platform with Trace-Based Root Cause Analysis",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(campaigns.router, prefix="/api/v1", tags=["campaigns"])
app.include_router(results.router, prefix="/api/v1", tags=["results"])
app.include_router(admin.router, prefix="/api/v1", tags=["admin"])


@app.get("/health", tags=["system"])
async def legacy_health() -> dict[str, str]:
    """Legacy health endpoint for backward compatibility."""
    return {"status": "ok", "service": "agenteval-api"}


@app.get("/campaigns", tags=["campaigns"])
async def list_campaigns() -> dict[str, list[dict[str, str]]]:
    """Temporary stub returning static campaign data."""
    return {
        "campaigns": [
            {
                "id": "demo-persona",
                "type": "persona",
                "status": "pending",
                "description": "Placeholder record until the orchestrator is available.",
            }
        ]
    }


def create_app() -> FastAPI:
    """Factory compatible with uvicorn's import style."""
    return app
