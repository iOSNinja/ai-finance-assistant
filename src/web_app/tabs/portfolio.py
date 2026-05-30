"""Portfolio tab: placeholder UI; agent lands in Phase 4."""

import streamlit as st


def render() -> None:
    st.markdown(
        '<div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">'
        '<h2 style="margin:0;">📊 Portfolio</h2>'
        '<span class="feature-badge badge-coming-soon">In development</span>'
        "</div>",
        unsafe_allow_html=True,
    )
    st.caption("Allocation, diversification, expense ratios, risk — at a glance.")

    st.markdown("")  # spacer

    # Load options
    st.markdown('<div class="section-eyebrow">Load a portfolio</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.button("📁  Load sample portfolio", use_container_width=True, disabled=True)
    with c2:
        st.button("✏️  Enter manually", use_container_width=True, disabled=True)
    with c3:
        st.button("📤  Import from CSV", use_container_width=True, disabled=True)

    st.markdown("---")

    # Preview metrics
    st.markdown('<div class="section-eyebrow">Overview</div>', unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    m1.metric("Total value",           "—", "—")
    m2.metric("Diversification score", "—", "—")
    m3.metric("Weighted expense",      "—", "—")

    st.markdown("---")

    st.markdown('<div class="section-eyebrow">What\'s coming</div>', unsafe_allow_html=True)
    st.markdown(
        """
        - Total portfolio value across all holdings
        - Asset allocation breakdown with interactive pie chart
        - Sector diversification score (Herfindahl-based)
        - Weighted expense ratio if fund tickers detected
        - Risk assessment based on equity-to-fixed-income ratio
        - Live price refresh via the Market Analysis agent
        """
    )