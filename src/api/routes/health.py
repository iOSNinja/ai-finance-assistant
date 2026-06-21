"""
Health check endpoint — used by load balancers and uptime monitors
to verify the service is alive.

The endpoint deliberately does NO work: no DB query, no LLM call, no
auth check. It just confirms "the FastAPI process is running and can
respond to HTTP." This is the standard pattern — health checks should
be fast and dependency-free so they don't cascade into outages.
"""

from fastapi import APIRouter
from pydantic import BaseModel

# APIRouter is FastAPI's way of grouping related endpoints in a separate
# file. Createing one router per route file and will "wire them in" inside main.py.
router = APIRouter(tags=["system"])


# Pydantic model for the response — type-safe, auto-documented.
class HealthResponse(BaseModel):
    status: str
    service: str


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Lightweight liveness check. Returns 200 OK if the server is alive."""
    return HealthResponse(status="ok", service="finnie-api")
