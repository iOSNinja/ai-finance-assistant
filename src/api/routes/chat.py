"""
POST /chat — Submit a finance question, get an answer + cost breakdown.

This is the main runtime endpoint. The flow:
  1. Receive query
  2. Check semantic cache (fast path — no LLM cost)
  3. On miss: invoke LangGraph wrapped in cost_tracker_for_request
  4. Cache the response with its compute cost
  5. Return answer + per-request cost info
"""
from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencies import get_assistant, get_semantic_cache
from src.api.models.chat import ChatRequest, ChatResponse, CostInfo
from src.main import FinnieAIFinanceAssistant
from src.observability.context import cost_tracker_for_request
from src.observability.cost_tracker import CostTracker
from src.observability.semantic_cache import SemanticCache
from src.utils.logger import setup_logger


router = APIRouter(tags=["chat"])
logger = setup_logger(__name__)


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    assistant: FinnieAIFinanceAssistant = Depends(get_assistant),
    cache: SemanticCache = Depends(get_semantic_cache),
) -> ChatResponse:
    """Submit a finance question. Returns the answer plus cost telemetry."""
    user_query = request.query

    # Per-request tracker — accumulates CostRecord entries from any LLM calls
    # that fire during this graph invocation (via the CostTrackingCallback).
    tracker = CostTracker(daily_budget_usd=5.00, per_query_alert_usd=0.10)

    try:
        # Cache check
        try:
            cached_response = cache.get(user_query)
        except Exception as cache_err:
            logger.warning(
                "Cache get failed — degrading to graph call",
                extra={"error_type": type(cache_err).__name__,
                       "error": str(cache_err)[:200]},
            )
            cached_response = None

        if cached_response is not None:
            # HIT
            return ChatResponse(
                response=cached_response,
                cost=CostInfo(
                    total_calls=0,
                    total_cost_usd=0.0,
                    cache_hit=True,
                    saved_by_cache_usd=0.0,    # tracked by cache directly
                ),
                per_agent={},
            )

        # MISS — run the graph
        cost_before = tracker.total_cost_usd
        with cost_tracker_for_request(tracker=tracker):
            response_text = assistant.ask(user_query, surface="api")
        query_cost = tracker.total_cost_usd - cost_before

        # Store in cache so a paraphrased query later HITs
        try:
            cache.put(user_query, response_text, cost_to_compute_usd=query_cost)
        except Exception as cache_err:
            logger.warning(
                "Cache put failed — response delivered anyway",
                extra={"error_type": type(cache_err).__name__,
                       "error": str(cache_err)[:200]},
            )

        return ChatResponse(
            response=response_text,
            cost=CostInfo(
                total_calls=tracker.total_calls,
                total_cost_usd=tracker.total_cost_usd,
                cache_hit=False,
                saved_by_cache_usd=0.0,
            ),
            per_agent=tracker.per_agent_summary(),
        )

    except Exception as e:
        logger.exception("Chat endpoint failed", extra={"error_type": type(e).__name__})
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {type(e).__name__}",
        )