"""
Unit tests for risk_engine.py.

These mock yfinance entirely so the suite runs offline and deterministically —
never hit a live API in tests. Run with:  pytest -v
"""

from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from risk_engine import Holding, Portfolio


def _fake_history(prices, index=None):
    """Build a fake OHLC history DataFrame the way yfinance would return it."""
    n = len(prices)
    idx = index or pd.date_range("2025-01-01", periods=n, freq="D")
    return pd.DataFrame({
        "Open": prices, "High": prices, "Low": prices, "Close": prices,
        "Volume": [1000] * n,
    }, index=idx)


@pytest.fixture
def two_stock_portfolio():
    return Portfolio([
        Holding("STOCK_A", shares=10, buy_price=100.0),
        Holding("STOCK_B", shares=5, buy_price=200.0),
    ], benchmark_ticker="BENCH")


def _mock_ticker_factory(price_map):
    """Returns a fake yf.Ticker(ticker) whose .history() reflects price_map[ticker]."""
    class FakeTickerObj:
        def __init__(self, ticker):
            self.ticker = ticker

        def history(self, period="1d"):
            prices = price_map.get(self.ticker)
            if prices is None:
                return pd.DataFrame()
            return _fake_history(prices)

    def fake_ticker(ticker):
        return FakeTickerObj(ticker)

    return fake_ticker


def test_price_snapshot_computes_pnl_correctly(two_stock_portfolio):
    price_map = {"STOCK_A": [110.0], "STOCK_B": [190.0]}
    with patch("risk_engine.yf.Ticker", side_effect=_mock_ticker_factory(price_map)):
        results = two_stock_portfolio.price_snapshot()

    a, b = results
    assert a.live_price == 110.0
    assert a.pnl == pytest.approx((110.0 - 100.0) * 10)
    assert a.return_pct == pytest.approx(10.0)
    assert b.pnl == pytest.approx((190.0 - 200.0) * 5)
    assert b.return_pct == pytest.approx(-5.0)


def test_price_snapshot_handles_missing_ticker_gracefully(two_stock_portfolio):
    price_map = {"STOCK_A": [110.0]}  # STOCK_B has no data
    with patch("risk_engine.yf.Ticker", side_effect=_mock_ticker_factory(price_map)):
        results = two_stock_portfolio.price_snapshot()

    a, b = results
    assert a.error is None
    assert b.error is not None
    assert b.current_value is None


def test_summary_totals(two_stock_portfolio):
    price_map = {"STOCK_A": [110.0], "STOCK_B": [190.0]}
    with patch("risk_engine.yf.Ticker", side_effect=_mock_ticker_factory(price_map)):
        summary = two_stock_portfolio.summary()

    assert summary["total_initial_value"] == pytest.approx(1000 + 1000)
    assert summary["total_current_value"] == pytest.approx(1100 + 950)
    assert summary["failed_tickers"] == []


def test_weights_sum_to_100(two_stock_portfolio):
    price_map = {"STOCK_A": [110.0], "STOCK_B": [190.0]}
    with patch("risk_engine.yf.Ticker", side_effect=_mock_ticker_factory(price_map)):
        results = two_stock_portfolio.price_snapshot()

    total_weight = sum(r.weight_pct for r in results if r.weight_pct is not None)
    assert total_weight == pytest.approx(100.0)


def test_risk_metrics_on_synthetic_series(two_stock_portfolio):
    # 30 days of gently trending, noisy prices so std/Sharpe/VaR are well-defined.
    rng = np.random.default_rng(seed=42)
    days = 30
    a_prices = 100 * np.cumprod(1 + rng.normal(0.001, 0.01, days))
    b_prices = 200 * np.cumprod(1 + rng.normal(0.0005, 0.015, days))
    bench_prices = 20000 * np.cumprod(1 + rng.normal(0.0007, 0.008, days))

    price_map = {"STOCK_A": a_prices, "STOCK_B": b_prices, "BENCH": bench_prices}
    with patch("risk_engine.yf.Ticker", side_effect=_mock_ticker_factory(price_map)):
        report = two_stock_portfolio.risk_report(period="1mo")

    assert report["annualized_volatility_pct"] is not None
    assert report["annualized_volatility_pct"] > 0
    assert report["max_drawdown_pct"] <= 0
    assert report["value_at_risk_95_pct"] is not None
    assert report["beta_vs_benchmark"] is not None


def test_no_data_returns_none_metrics(two_stock_portfolio):
    with patch("risk_engine.yf.Ticker", side_effect=_mock_ticker_factory({})):
        report = two_stock_portfolio.risk_report()

    assert report["annualized_volatility_pct"] is None
    assert report["sharpe_ratio"] is None
    assert report["max_drawdown_pct"] is None


def test_from_csv_supports_arbitrary_number_of_holdings(tmp_path):
    csv_path = tmp_path / "portfolio.csv"
    csv_path.write_text(
        "Ticker,Shares,Buy_Price\n"
        "A.NS,1,10\nB.NS,2,20\nC.NS,3,30\nD.NS,4,40\nE.NS,5,50\n"
    )
    portfolio = Portfolio.from_csv(str(csv_path))
    assert len(portfolio.holdings) == 5


def test_from_csv_missing_column_raises(tmp_path):
    csv_path = tmp_path / "bad.csv"
    csv_path.write_text("Ticker,Shares\nA.NS,1\n")
    with pytest.raises(ValueError):
        Portfolio.from_csv(str(csv_path))


def test_empty_portfolio_raises():
    with pytest.raises(ValueError):
        Portfolio([])
