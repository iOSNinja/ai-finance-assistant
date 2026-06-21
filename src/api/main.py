"""
src/api/main.py — FastAPI application entry point.

Run with:
    uv run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

The --reload flag auto-restarts the server when you change a Python file.
Great for dev; not in production.
"""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.routes import chat, health
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup and shutdown hooks for the FastAPI app.

    Code BEFORE `yield` runs on startup (after the app boots, before
    accepting requests). Code AFTER `yield` runs on shutdown (when the
    server is stopping).

    Will use this later to pre-warm the LangGraph singleton and
    semantic cache so first-request latency is low.
    """
    # Startup
    logger.info("Finnie API starting up")
    yield
    # Shutdown
    logger.info("Finnie API shutting down")


# Create the FastAPI application instance.
# title/version/description show up in the /docs Swagger UI.
app = FastAPI(
    title="Finnie API",
    version="0.1.0",
    description="Multi-agent personal finance education assistant",
    lifespan=lifespan,
)

# Wiring each route router into the main app.
app.include_router(health.router)
app.include_router(chat.router)