"""Pydantic models for /chat request and response."""

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Inbound payload for POST /chat."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="The user's natural-language finance question",
    )


class CostInfo(BaseModel):
    """Per-request cost breakdown for the response."""

    total_calls: int
    total_cost_usd: float
    cache_hit: bool
    saved_by_cache_usd: float


class ChatResponse(BaseModel):
    """Outbound payload from POST /chat."""

    response: str = Field(..., description="Finnie's full text response")
    cost: CostInfo
    per_agent: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="Per-agent breakdown — same shape as CostTracker.per_agent_summary()",
    )
