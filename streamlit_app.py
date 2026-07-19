"""
Streamlit frontend for the Portfolio Risk & Trading Engine.

Run locally:
    streamlit run streamlit_app.py

Deploy for free:
    Push this repo to GitHub (public), then deploy at https://share.streamlit.io
    pointing it at streamlit_app.py. See README.md for the full walkthrough.
"""

import io

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from risk_engine import Holding, Portfolio

st.set_page_config(page_title="Portfolio Risk Dashboard", page_icon="📊", layout="wide")

DEFAULT_PORTFOLIO = pd.DataFrame({
    "Ticker": ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS"],
    "Shares": [10, 5, 8, 12, 15],
    "Buy_Price": [2400.00, 3800.00, 1500.00, 1550.00, 1050.00],
})

st.title("📊 Real-Time Portfolio Risk & Trading Dashboard")
st.caption("Live prices via Yahoo Finance · risk metrics computed on a 1-year lookback")

# ------------------------------------------------------------------ sidebar

with st.sidebar:
    st.header("Portfolio Setup")
    uploaded = st.file_uploader("Upload a portfolio CSV", type=["csv"],
                                 help="Columns required: Ticker, Shares, Buy_Price")
    benchmark = st.text_input("Benchmark ticker (for beta)", value="^NSEI")
    lookback = st.selectbox("Risk lookback period", ["6mo", "1y", "2y", "5y"], index=1)
    st.caption("Tip: use .NS suffix for NSE tickers, .BO for BSE, or plain tickers for US stocks.")

if uploaded is not None:
    base_df = pd.read_csv(uploaded)
else:
    base_df = DEFAULT_PORTFOLIO.copy()

st.subheader("Holdings")
edited_df = st.data_editor(
    base_df,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Shares": st.column_config.NumberColumn(min_value=0, step=1),
        "Buy_Price": st.column_config.NumberColumn(min_value=0.0, format="%.2f"),
    },
)

refresh = st.button("🔄 Fetch live prices & compute risk", type="primary")

# ------------------------------------------------------------------ main

if refresh:
    edited_df = edited_df.dropna(subset=["Ticker", "Shares", "Buy_Price"])
    if edited_df.empty:
        st.warning("Add at least one holding first.")
        st.stop()

    holdings = [Holding(str(r.Ticker).strip(), float(r.Shares), float(r.Buy_Price))
                for r in edited_df.itertuples()]

    with st.spinner("Fetching live prices..."):
        portfolio = Portfolio(holdings, benchmark_ticker=benchmark)
        results = portfolio.price_snapshot()
        summary = portfolio.summary(results)

    failed = [r.ticker for r in results if r.error]
    if failed:
        st.warning(f"Could not fetch data for: {', '.join(failed)} (bad ticker, delisted, or rate-limited)")

    valid_results = [r for r in results if r.current_value is not None]
    if not valid_results:
        st.error("No live data returned for any holding. Check your tickers and try again.")
        st.stop()

    # --- top-line metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Invested Capital", f"₹{summary['total_initial_value']:,.0f}")
    col2.metric("Current Value", f"₹{summary['total_current_value']:,.0f}")
    col3.metric("Net P&L", f"₹{summary['total_pnl']:+,.0f}", f"{summary['total_return_pct']:+.2f}%")

    # --- holdings table
    display_df = pd.DataFrame([{
        "Ticker": r.ticker, "Shares": r.shares, "Buy Price": r.buy_price,
        "Live Price": r.live_price, "Value": r.current_value,
        "P&L": r.pnl, "Return %": r.return_pct, "Weight %": r.weight_pct,
    } for r in valid_results])
    st.dataframe(
        display_df.style.format({
            "Buy Price": "₹{:.2f}", "Live Price": "₹{:.2f}", "Value": "₹{:,.2f}",
            "P&L": "₹{:+,.2f}", "Return %": "{:+.2f}%", "Weight %": "{:.1f}%",
        }),
        use_container_width=True,
    )

    # --- allocation + P&L charts
    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        fig_pie = px.pie(display_df, names="Ticker", values="Value", title="Portfolio Allocation")
        st.plotly_chart(fig_pie, use_container_width=True)
    with chart_col2:
        fig_bar = px.bar(display_df, x="Ticker", y="P&L", color="P&L",
                          color_continuous_scale="RdYlGn", title="P&L by Holding")
        st.plotly_chart(fig_bar, use_container_width=True)

    # --- risk metrics
    st.subheader("Risk Metrics")
    with st.spinner("Computing risk metrics..."):
        risk = portfolio.risk_report(period=lookback)

    if risk["annualized_volatility_pct"] is not None:
        rcol1, rcol2, rcol3, rcol4, rcol5 = st.columns(5)
        rcol1.metric("Volatility (ann.)", f"{risk['annualized_volatility_pct']:.2f}%")
        rcol2.metric("Sharpe Ratio", f"{risk['sharpe_ratio']:.2f}" if risk['sharpe_ratio'] is not None else "N/A")
        rcol3.metric("Max Drawdown", f"{risk['max_drawdown_pct']:.2f}%")
        rcol4.metric("VaR (95%, 1-day)", f"{risk['value_at_risk_95_pct']:.2f}%")
        rcol5.metric(f"Beta vs {risk['benchmark']}",
                     f"{risk['beta_vs_benchmark']:.2f}" if risk['beta_vs_benchmark'] is not None else "N/A")
    else:
        st.info("Not enough historical price data to compute risk metrics for this lookback period.")

    # --- download report
    csv_buffer = io.StringIO()
    display_df.to_csv(csv_buffer, index=False)
    st.download_button("⬇️ Download report as CSV", csv_buffer.getvalue(),
                        file_name="portfolio_report.csv", mime="text/csv")
else:
    st.info("Edit your holdings above, then click **Fetch live prices & compute risk**.")
