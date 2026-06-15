"""Sidebar: session controls, about, compliance, cost & performance."""

import streamlit as st


def render_sidebar() -> None:
    with st.sidebar:
        # Brand block
        st.markdown(
            """
            <div style="padding: 8px 0 16px 0;">
            <div style="font-family: 'Outfit', sans-serif; font-size: 1.5rem;
                        font-weight: 800; color: #fafafa;">
                🦊 Finnie
            </div>
            <div style="font-size: 0.8rem; color: #71717a; margin-top: 2px;">
                AI-powered finance tutor
            </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("---")
        st.markdown("### Conversation")
        if st.button("Start new conversation", use_container_width=True):
            _reset_conversation()
            st.rerun()
        st.caption("Clears chat history and resets cost tracking.")

        st.markdown("---")
        st.markdown("### Agents")
        st.markdown(
            """
            <div style="display: flex; flex-direction: column; gap: 6px;">
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="color: #a1a1aa; font-size: 0.85rem;">Finance Q&amp;A</span>
                <span class="feature-badge badge-live">Live</span>
              </div>
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="color: #a1a1aa; font-size: 0.85rem;">Market Analysis</span>
                <span class="feature-badge badge-live">Live</span>
              </div>
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="color: #a1a1aa; font-size: 0.85rem;">Portfolio Analysis</span>
                <span class="feature-badge badge-live">Live</span>
              </div>
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="color: #a1a1aa; font-size: 0.85rem;">Goal Planning</span>
                <span class="feature-badge badge-live">Live</span>
              </div>
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="color: #a1a1aa; font-size: 0.85rem;">News Synthesizer</span>
                <span class="feature-badge badge-live">Live</span>
              </div>
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="color: #a1a1aa; font-size: 0.85rem;">Tax Education</span>
                <span class="feature-badge badge-live">Live</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Live cost & performance panel
        st.markdown("---")
        st.markdown("### 💰 Cost & Performance")
        _render_cost_panel()

        st.markdown("---")
        st.markdown("### About")
        st.caption(
            "Finnie is a multi-agent AI assistant for personal finance "
            "education. Built with LangGraph, RAG, and OpenAI."
        )

        st.markdown("---")
        st.warning(
            "**Educational content only.** Not personalized financial advice. "
            "Consult a qualified advisor for decisions specific to your situation.",
            icon="⚠️",
        )

def _format_cost(usd: float) -> str:
    """Format a USD amount for compact sidebar display.

    Strategy:
      - very small (< $0.01) → cents with 4 decimals, e.g. "0.0912¢"
      - small ($0.01 – $1)   → dollars with 4 decimals, e.g. "$0.0123"
      - normal (≥ $1)        → dollars with 2 decimals, e.g. "$1.23"

    Why cents under $0.01: shows real signal without leading zeros that
    dominate the eye.
    """
    if usd <= 0:
        return "$0.00"
    if usd < 0.01:
        return f"{usd * 100:.4f}¢"     # e.g. 0.0912¢
    if usd < 1.0:
        return f"${usd:.4f}"           # e.g. $0.0234
    return f"${usd:,.2f}"              # e.g. $1.23 or $1,234.56


def _render_cost_panel() -> None:
    """Render live cost stats from the session's CostTracker.

    Reads st.session_state.cost_tracker (set per chat session in chat.py).
    Shows top-level KPIs as st.metric tiles + a per-agent breakdown expander +
    an alerts expander (if any alerts fired).
    """
    tracker = st.session_state.get("cost_tracker")
    if tracker is None or tracker.total_calls == 0:
        st.caption("Send a chat query to see cost breakdown.")
        return

    # Top-level KPI tiles (2x2 grid)
    # Single-column layout — each tile gets the full sidebar width, so
    # precise dollar values like $0.000912 fit without truncation.
    st.metric("LLM calls", tracker.total_calls)
    st.metric("Total spent", _format_cost(tracker.total_cost_usd))
    st.metric("Avg / call",  _format_cost(tracker.avg_cost_per_call_usd))
    st.metric("Cache hit rate", f"{tracker.cache_hit_rate:.0%}")

    # Per-agent breakdown (collapsed by default)
    with st.expander("Per-agent breakdown"):
        summary = tracker.per_agent_summary()
        if not summary:
            st.caption("No data yet.")
        else:
            for agent, stats in sorted(summary.items()):
                st.markdown(
                    f"**{agent}** &nbsp;·&nbsp; "
                    f"{stats['call_count']} call{'s' if stats['call_count'] != 1 else ''} "
                    f"&nbsp;·&nbsp; ${stats['total_cost_usd']:.6f} "
                    f"&nbsp;·&nbsp; in={stats['total_prompt_tokens']} "
                    f"out={stats['total_completion_tokens']} "
                    f"&nbsp;·&nbsp; {stats['avg_latency_ms']:.0f}ms avg",
                    unsafe_allow_html=True,
                )

    # Alerts panel (only shown if any alerts fired)
    if tracker.alerts:
        with st.expander(f"⚠️ Alerts ({len(tracker.alerts)})", expanded=True):
            for alert in tracker.alerts:
                st.warning(alert, icon="⚠️")


def _reset_conversation() -> None:
    """Clear chat history AND reset accumulated cost tracking."""
    if "chat_messages" in st.session_state:
        st.session_state.chat_messages = []
    if "cost_tracker" in st.session_state:
        st.session_state.cost_tracker.reset()
    if "assistant" in st.session_state:
        st.session_state.assistant._new_session()