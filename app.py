"""
Real-Time FinTech Portfolio Risk & Trading Dashboard (CLI)
===========================================================
Reads holdings from portfolio.csv (any number of rows — not hardcoded to
3 stocks), fetches live prices, and prints P&L plus institutional risk
metrics. All the actual math lives in risk_engine.py...

Usage:
    python app.py
    python app.py --portfolio my_holdings.csv --benchmark ^NSEI...
"""

import argparse

from risk_engine import Portfolio


def format_currency(value: float) -> str:
    return f"\u20b9{value:,.2f}"


def print_dashboard(portfolio: Portfolio) -> None:
    print("=== LIVE FINTECH PORTFOLIO TRADING DASHBOARD ===")
    print("Fetching live data...\n")

    results = portfolio.price_snapshot()

    for r in results:
        if r.error:
            print(f"⚠️  [{r.ticker}] {r.error}")
            continue
        print(f"[{r.ticker}] Shares: {r.shares:g} | Buy: {format_currency(r.buy_price)} "
              f"| Live: {format_currency(r.live_price)} | Weight: {r.weight_pct:.1f}%")
        print(f"       P&L: {r.pnl:+,.2f} ({r.return_pct:+.2f}%)\n")

    summary = portfolio.summary(results)
    if summary["total_initial_value"] > 0:
        print("=" * 46)
        print(f"Total Invested Capital : {format_currency(summary['total_initial_value'])}")
        print(f"Current Portfolio Value: {format_currency(summary['total_current_value'])}")
        print(f"Net Portfolio P&L      : {summary['total_pnl']:+,.2f} "
              f"({summary['total_return_pct']:+.2f}%)")
        print("=" * 46)

    print("\n=== RISK METRICS (1-year lookback) ===")
    risk = portfolio.risk_report(period="1y")
    if risk["annualized_volatility_pct"] is not None:
        print(f"Annualized Volatility  : {risk['annualized_volatility_pct']:.2f}%")
        print(f"Sharpe Ratio           : {risk['sharpe_ratio']:.2f}")
        print(f"Max Drawdown           : {risk['max_drawdown_pct']:.2f}%")
        print(f"1-Day VaR (95%)        : {risk['value_at_risk_95_pct']:.2f}%")
        print(f"Beta vs {risk['benchmark']:<10}   : "
              f"{risk['beta_vs_benchmark']:.2f}" if risk['beta_vs_benchmark'] is not None
              else f"Beta vs {risk['benchmark']}: unavailable")
    else:
        print("Not enough historical data to compute risk metrics.")

    if summary["failed_tickers"]:
        print(f"\n⚠️  Skipped (no data): {', '.join(summary['failed_tickers'])}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Live portfolio risk dashboard")
    parser.add_argument("--portfolio", default="portfolio.csv",
                         help="CSV with columns Ticker, Shares, Buy_Price")
    parser.add_argument("--benchmark", default="^NSEI",
                         help="Benchmark index ticker for beta calculation")
    args = parser.parse_args()

    portfolio = Portfolio.from_csv(args.portfolio, benchmark_ticker=args.benchmark)
    print_dashboard(portfolio)


if __name__ == "__main__":
    main()
