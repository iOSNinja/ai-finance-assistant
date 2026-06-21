"""
src/web_app/components/cloud_mode.py — Cloud-deployment-mode helper.

When running on Streamlit Cloud as a chat-only demo, non-chat tabs
show a "use the local version" banner instead of their normal content.
Controlled by the FINNIE_CHAT_ONLY_MODE env var.

Local development: env var not set -> all tabs work normally.
Streamlit Cloud:   env var set to 'true' -> only chat tab functions.
"""

import os

import streamlit as st

CHAT_ONLY_CLOUD_MODE = os.environ.get("FINNIE_CHAT_ONLY_MODE", "false").lower() == "true"


def render_cloud_only_notice(tab_name: str) -> bool:
    """Show a 'use local version' banner if running in chat-only cloud mode.

    Returns True if banner was shown (caller should 'return' to skip tab body).
    Returns False when running locally (caller proceeds with normal tab body).

    Usage in each non-chat tab's render():
        def render():
            if render_cloud_only_notice("Portfolio"):
                return
            # ... existing tab code unchanged
    """
    if not CHAT_ONLY_CLOUD_MODE:
        return False

    st.markdown(
        f"""
        ### 🚧 The **{tab_name}** tab is **available in the full local version** — [see GitHub](https://github.com/iOSNinja/ai-finance-assistant)

        This public cloud demo features only the **Chat tab** to keep the
        deployment light and costs bounded. The full experience — including
        this {tab_name} tab — runs locally in ~3 minutes.

        **Try it locally:**
```bash
        git clone https://github.com/iOSNinja/ai-finance-assistant
        cd ai-finance-assistant
        uv sync
        uv run python -m spacy download en_core_web_sm
        uv run python -m src.rag.ingest

        # Terminal A — FastAPI backend
        uv run uvicorn src.api.main:app --port 8000

        # Terminal B — Streamlit UI
        uv run streamlit run src/web_app/app.py
```

        💬 **Click the Chat tab above to try Finnie's multi-agent system live!**
        """,
        unsafe_allow_html=True,
    )
    return True
