"""Chat tab: main multi-agent conversational interface."""

import os

import httpx
import streamlit as st

from src.core.config import embeddings
from src.main import FinnieAIFinanceAssistant
from src.observability.cost_tracker import CostTracker
from src.observability.semantic_cache import SemanticCache
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# FastAPI backend URL — env var first (cloud), localhost fallback (local dev)
API_BASE_URL = os.environ.get("FINNIE_API_URL", "http://localhost:8000")

# Per-session rate limit — UX courtesy for trusted demo users.
# (Real cost protection is server-side in the FastAPI cost circuit breaker.)
CHAT_QUERY_LIMIT = 3

USER_AVATAR = "🧑"
FINNIE_AVATAR = "🦊"

EXAMPLE_PROMPTS = [
    ("📘", "What is an ETF?"),
    ("💡", "Explain compound interest like I'm 10"),
    ("⚖️", "Index fund vs mutual fund?"),
    ("🌿", "Why is diversification important?"),
]


def _get_assistant() -> FinnieAIFinanceAssistant:
    if "assistant" not in st.session_state:
        with st.spinner("Waking Finnie up (loading knowledge base)..."):
            st.session_state.assistant = FinnieAIFinanceAssistant()
    return st.session_state.assistant


def _ensure_session_tracker() -> CostTracker:
    if "cost_tracker" not in st.session_state:
        st.session_state.cost_tracker = CostTracker(
            daily_budget_usd=5.00,
            per_query_alert_usd=0.10,
        )
    return st.session_state.cost_tracker


# session-scoped SemanticCache
def _ensure_session_cache() -> SemanticCache:
    """One SemanticCache per Streamlit chat session.

    Threshold is calibrated against text-embedding-3-small.
    Cache lives in memory only; cleared on 'Start new conversation'.
    """
    if "semantic_cache" not in st.session_state:
        st.session_state.semantic_cache = SemanticCache(
            embeddings=embeddings,
            threshold=0.75,  # Calibrated against 39 labeled pairs; zero FPs at 83% recal
            ttl_seconds=3600.0,  # 1 hour
            max_size=100,
        )
    return st.session_state.semantic_cache


def _init_state() -> None:
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []


def _render_history() -> None:
    for msg in st.session_state.chat_messages:
        avatar = USER_AVATAR if msg["role"] == "user" else FINNIE_AVATAR
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])


def _handle_query(user_query: str) -> None:
    # Per-session rate limit
    used = st.session_state.get("chat_queries_used", 0)
    if used >= CHAT_QUERY_LIMIT:
        st.warning(
            f"⛔ You've used your **{CHAT_QUERY_LIMIT} free chat queries** for this session. "
            f"Want to try more? Please contact "
            f"[Ravi on LinkedIn](https://www.linkedin.com/in/ravi-doddi-32061110/) "
            f"for extended access.",
            icon="🦊",
        )
        return

    st.session_state.chat_queries_used = used + 1
    remaining = CHAT_QUERY_LIMIT - st.session_state.chat_queries_used
    if remaining <= 1:
        st.info(
            f"ℹ️ {remaining} free chat {'query' if remaining == 1 else 'queries'} remaining "
            f"in this session.",
            icon="📊",
        )

    st.session_state.chat_messages.append({"role": "user", "content": user_query})
    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(user_query)

    tracker = _ensure_session_tracker()  # for sidebar cumulative display

    with st.chat_message("assistant", avatar=FINNIE_AVATAR):
        with st.spinner("Researching..."):
            try:
                # Call FastAPI backend via HTTP
                with httpx.Client(timeout=60.0) as client:
                    resp = client.post(
                        f"{API_BASE_URL}/chat",
                        json={"query": user_query},
                    )
                    resp.raise_for_status()
                    payload = resp.json()

                response = payload["response"]
                cost_info = payload.get("cost", {})

                # Update sidebar tracker with the per-request cost
                _accumulate_cost_into_session_tracker(
                    tracker, cost_info, payload.get("per_agent", {})
                )

            except httpx.HTTPStatusError as e:
                logger.exception("FastAPI returned an error")
                response = (
                    "The backend returned an error. Please try again.\n\n"
                    f"_({e.response.status_code})_"
                )
            except httpx.RequestError:
                logger.exception("Couldn't reach FastAPI backend")
                response = (
                    "Couldn't reach the backend. Is it running?\n\n"
                    "Start with: `uv run uvicorn src.api.main:app --reload --port 8000`"
                )
            except Exception as e:
                logger.exception("Unexpected error calling FastAPI")
                response = f"Unexpected error: {type(e).__name__}"

        st.markdown(response)

    st.session_state.chat_messages.append({"role": "assistant", "content": response})


def _accumulate_cost_into_session_tracker(tracker, cost_info: dict, per_agent: dict) -> None:
    """Bridge: take the FastAPI response's cost info and merge it into the
    Streamlit session tracker so the sidebar shows cumulative session cost."""
    from src.observability.cost_tracker import CostRecord

    # Synthesize one combined record from the per-agent breakdown
    for agent_name, stats in per_agent.items():
        if stats.get("call_count", 0) == 0:
            continue
        # Push one CostRecord per agent into the session tracker.
        # Note: trace_id is synthetic here since we don't have one from API.
        tracker.record(
            CostRecord(
                trace_id=f"api-{agent_name[:6]}",
                agent_name=agent_name,
                model="gpt-4o-mini",
                prompt_tokens=int(stats.get("total_prompt_tokens", 0)),
                completion_tokens=int(stats.get("total_completion_tokens", 0)),
                cost_usd=float(stats.get("total_cost_usd", 0)),
                latency_ms=float(stats.get("avg_latency_ms", 0)),
                cache_hit=cost_info.get("cache_hit", False),
            )
        )


def render() -> None:
    _init_state()

    _render_history()

    if not st.session_state.chat_messages:
        st.markdown(
            '<div class="section-eyebrow">Try a starter question</div>',
            unsafe_allow_html=True,
        )
        cols = st.columns(2)
        for i, (icon, prompt) in enumerate(EXAMPLE_PROMPTS):
            with cols[i % 2]:
                if st.button(f"{icon}  {prompt}", use_container_width=True, key=f"ex_{i}"):
                    _handle_query(prompt)
                    st.rerun()

    if user_query := st.chat_input("Ask Finnie anything about finance..."):
        _handle_query(user_query)
        st.rerun()
