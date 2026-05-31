"""Goals tab: wired to goal-planning tools for instant projections + chart."""

import streamlit as st
import pandas as pd

from src.agents.goal.tool import project_growth, required_monthly_savings


def _render_required_monthly(result: dict) -> None:
    """Display result of required_monthly_savings."""
    monthly = result["monthly_contribution"]

    if monthly == 0 and "note" in result:
        st.success(f"**$0/month required.** {result['note']}")
        return

    st.markdown(
        f'<div class="finnie-card">'
        f'<div class="section-eyebrow">Required monthly savings</div>'
        f'<div style="font-size:3rem;font-weight:800;font-family:Outfit,sans-serif;'
        f'background:var(--gradient-hero);-webkit-background-clip:text;'
        f'-webkit-text-fill-color:transparent;background-clip:text;">'
        f'${monthly:,.0f}'
        f'</div>'
        f'<div style="color:var(--text-secondary);">per month, for {result["years"]} years '
        f'at {result["expected_annual_return_pct"]:.1f}% annual return</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Target",            f"${result['target_amount']:,.0f}")
    c2.metric("Total you contribute", f"${result['total_contributed']:,.0f}")
    c3.metric("Total growth",      f"${result['growth_from_contributions'] + result['growth_from_current_savings']:,.0f}")


def _render_projection(result: dict) -> None:
    """Display result of project_growth — metrics + line chart."""
    c1, c2, c3 = st.columns(3)
    c1.metric("Final balance",     f"${result['final_balance']:,.0f}")
    c2.metric("Total contributed", f"${result['total_contributed']:,.0f}")
    c3.metric("Total growth",      f"${result['total_growth']:,.0f}")

    if result["yearly_balances"]:
        df = pd.DataFrame(result["yearly_balances"])
        df = df.set_index("year")
        st.markdown("### Year-by-year")
        st.line_chart(df[["balance", "contributed_to_date"]])
        with st.expander("Show table"):
            st.dataframe(df, use_container_width=True)


def render() -> None:
    st.markdown(
        '<div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">'
        '<h2 style="margin:0;">🎯 Goals</h2>'
        '<span class="feature-badge badge-live">Live</span>'
        "</div>",
        unsafe_allow_html=True,
    )
    st.caption("Project savings toward retirement, a home, education — anything.")

    st.markdown("")

    mode = st.radio(
        "What are you solving for?",
        ["How much to save per month?", "What will I have at the end?"],
        horizontal=True,
        label_visibility="collapsed",
    )

    if mode == "How much to save per month?":
        st.markdown('<div class="section-eyebrow">Goal calculator — solve for monthly savings</div>', unsafe_allow_html=True)
        c_left, c_right = st.columns(2)
        with c_left:
            target = st.number_input("Target amount ($)", min_value=1000, value=1_000_000, step=10_000)
            years  = st.number_input("Time horizon (years)", min_value=1, max_value=60, value=30)
        with c_right:
            current = st.number_input("Current savings ($)", min_value=0, value=10_000, step=1000)
            ret_pct = st.slider("Expected annual return (%)", 1.0, 15.0, 7.0, 0.5)

        if st.button("📊  Calculate", use_container_width=True, type="primary"):
            try:
                result = required_monthly_savings.invoke({
                    "target_amount":              float(target),
                    "years":                      int(years),
                    "expected_annual_return_pct": float(ret_pct),
                    "current_savings":            float(current),
                })
            except Exception as e:
                st.error(f"{type(e).__name__}: {e}")
                return
            st.markdown("---")
            _render_required_monthly(result)

    else:
        st.markdown('<div class="section-eyebrow">Projection — solve for final balance</div>', unsafe_allow_html=True)
        c_left, c_right = st.columns(2)
        with c_left:
            current = st.number_input("Current savings ($)", min_value=0, value=10_000, step=1000)
            monthly = st.number_input("Monthly contribution ($)", min_value=0, value=500, step=50)
        with c_right:
            years   = st.number_input("Time horizon (years)", min_value=1, max_value=60, value=30)
            ret_pct = st.slider("Expected annual return (%)", 1.0, 15.0, 7.0, 0.5)

        if st.button("📈  Project growth", use_container_width=True, type="primary"):
            try:
                result = project_growth.invoke({
                    "current_savings":            float(current),
                    "monthly_contribution":       float(monthly),
                    "years":                      int(years),
                    "expected_annual_return_pct": float(ret_pct),
                })
            except Exception as e:
                st.error(f"{type(e).__name__}: {e}")
                return
            st.markdown("---")
            _render_projection(result)

    st.markdown("---")
    st.caption(
        "⚠️ These projections assume a constant return and don't account for "
        "inflation, taxes, or fees. Markets are volatile — use this as a starting "
        "point, not a guarantee. For personalized planning, consult a CPA or CFP."
    )