"""Portfolio tab: placeholder UI; Portfolio Analysis Agent lands in Phase 4."""

import streamlit as st


def render() -> None:
    st.markdown("## 📊 Portfolio Analysis")
    st.caption("Analyze your holdings: allocation, diversification, expense ratios, risk.")

    st.info(
        "🚧 **Portfolio Analysis Agent is in active development.** "
        "UI controls are visible below as a preview — they'll go live in Phase 4."
    )

    # --- Load options ---
    st.markdown("### Load your portfolio")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.button(
            "📁 Load sample portfolio",
            use_container_width=True,
            disabled=True,
        )
    with col2:
        st.button(
            "✏️ Enter manually",
            use_container_width=True,
            disabled=True,
        )
    with col3:
        st.button(
            "📤 Import from CSV",
            use_container_width=True,
            disabled=True,
        )

    st.divider()

    # --- Placeholder dashboard ---
    st.markdown("### Portfolio Overview")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("Total value", "—", "—")
    with col_b:
        st.metric("Diversification", "—", "—")
    with col_c:
        st.metric("Weighted expense ratio", "—", "—")

    st.divider()
    st.markdown("### Coming in Phase 4")
    st.markdown(
        """
        - **Total portfolio value** across all holdings
        - **Asset allocation breakdown** (stocks / bonds / cash) with pie chart
        - **Sector diversification score** (Herfindahl-based)
        - **Weighted expense ratio** if fund tickers detected
        - **Risk assessment** based on equity-to-fixed-income ratio
        - **Live price refresh** (via the Market Analysis Agent)
        """
    )