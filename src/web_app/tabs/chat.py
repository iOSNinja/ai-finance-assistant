"""Chat tab: main multi-agent conversational interface."""

import streamlit as st

from src.core.config import embeddings
from src.main import FinnieAIFinanceAssistant
from src.observability.context import cost_tracker_for_request
from src.observability.cost_tracker import CostTracker
from src.observability.semantic_cache import SemanticCache
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

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
    st.session_state.chat_messages.append({"role": "user", "content": user_query})
    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(user_query)

    assistant = _get_assistant()
    tracker = _ensure_session_tracker()
    cache = _ensure_session_cache()

    with st.chat_message("assistant", avatar=FINNIE_AVATAR):
        with st.spinner("Researching..."):
            try:
                # CACHE-ASIDE PATTERN
                # 1. Try the cache first. Graceful degradation: if the cache
                #    call itself fails, treat it as a miss and run the graph.
                try:
                    cached_response = cache.get(user_query)
                except Exception as cache_err:
                    logger.warning(
                        "Cache get failed — falling back to graph",
                        extra={
                            "error_type": type(cache_err).__name__,
                            "error": str(cache_err)[:200],
                        },
                    )
                    cached_response = None

                if cached_response is not None:
                    # 2. Cache HIT — return immediately. Zero LLM cost.
                    response = cached_response
                    logger.info(
                        "Cache hit",
                        extra={
                            "query_preview": user_query[:60],
                            "hit_rate": cache.hit_rate,
                        },
                    )
                else:
                    # 3. Cache MISS — snapshot cost, run graph, then store.
                    cost_before = tracker.total_cost_usd
                    with cost_tracker_for_request(tracker=tracker):
                        response = assistant.ask(user_query, surface="streamlit")
                    query_cost = tracker.total_cost_usd - cost_before

                    # 4. Write-through: store result + its cost (for $ saved math).
                    try:
                        cache.put(user_query, response, cost_to_compute_usd=query_cost)
                    except Exception as cache_err:
                        # Cache put failure is also non-fatal — just log it.
                        logger.warning(
                            "Cache put failed — response delivered anyway",
                            extra={
                                "error_type": type(cache_err).__name__,
                                "error": str(cache_err)[:200],
                            },
                        )
            except Exception as e:
                logger.exception("Graph invocation failed in chat tab")
                response = (
                    "Sorry — something went wrong while answering. "
                    "Please try again or rephrase your question.\n\n"
                    f"_({type(e).__name__})_"
                )
        st.markdown(response)

    st.session_state.chat_messages.append({"role": "assistant", "content": response})


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
