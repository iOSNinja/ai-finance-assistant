"""
POST /chat — Submit a finance question, get an answer + cost breakdown.

This is the main runtime endpoint. The flow:
  1. Receive query
  2. Check semantic cache (fast path — no LLM cost)
  3. On miss: invoke LangGraph wrapped in cost_tracker_for_request
  4. Cache the response with its compute cost
  5. Return answer + per-request cost info
"""

from fastapi import APIRouter, Depends, HTTPException, Request

from src.api.dependencies import get_assistant, get_daily_tracker, get_semantic_cache
from src.api.models.chat import ChatRequest, ChatResponse, CostInfo
from src.api.rate_limit import limiter
from src.main import FinnieAIFinanceAssistant
from src.observability.context import cost_tracker_for_request
from src.observability.cost_tracker import CostTracker
from src.observability.semantic_cache import SemanticCache
from src.utils.logger import setup_logger

router = APIRouter(tags=["chat"])
logger = setup_logger(__name__)


# Per-IP rate limit on /chat:
#   - 5 requests per minute -> bursts allowed for legitimate users
#   - 30 requests per day per IP -> bot defense
# Even blocked requests still cost ALB LCU + Fargate CPU, so we cap aggressively.
@router.post("/chat", response_model=ChatResponse)
@limiter.limit("5/minute;30/day")
async def chat(
    request: Request,  # required by slowapi to read client IP
    chat_request: ChatRequest,
    assistant: FinnieAIFinanceAssistant = Depends(get_assistant),
    cache: SemanticCache = Depends(get_semantic_cache),
) -> ChatResponse:
    """Submit a finance question. Returns the answer plus cost telemetry."""
    # Demo budget circuit breaker
    daily_tracker = get_daily_tracker()
    if daily_tracker.total_cost_usd >= daily_tracker.daily_budget_usd:
        logger.warning(
            "Demo budget exhausted",
            extra={
                "total_spent_usd": round(daily_tracker.total_cost_usd, 4),
                "budget_usd": daily_tracker.daily_budget_usd,
            },
        )
        raise HTTPException(
            status_code=429,
            detail=(
                "Demo budget exhausted for today. "
                "Please contact Ravi (linkedin.com/in/ravi-doddi-32061110) "
                "for extended access."
            ),
        )

    user_query = chat_request.query

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
                extra={"error_type": type(cache_err).__name__, "error": str(cache_err)[:200]},
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
                    saved_by_cache_usd=0.0,  # tracked by cache directly
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
                extra={"error_type": type(cache_err).__name__, "error": str(cache_err)[:200]},
            )

        # Also record this query's cost into the process-wide daily budget.
        # This is what the circuit breaker checks at the start of next request.
        from src.observability.cost_tracker import CostRecord

        daily_tracker.record(
            CostRecord(
                trace_id=f"daily-{daily_tracker.total_calls}",
                agent_name="aggregate",
                model="gpt-4o-mini",
                prompt_tokens=0,
                completion_tokens=0,
                cost_usd=query_cost,
                latency_ms=0.0,
                cache_hit=False,
            )
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
        ) from e
