# Real-Time Portfolio Risk & Trading Dashboard

A portfolio tracker that pulls live prices from Yahoo Finance and computes
both P&L and institutional-style risk metrics (volatility, Sharpe ratio,
max drawdown, Value at Risk, beta vs. a benchmark index). Ships with a CLI
and a Streamlit web dashboard, both built on the same engine.

## Why this structure

- **`risk_engine.py`** — all the math (pricing, P&L, risk metrics). No UI code.
- **`app.py`** — command-line dashboard, for quick checks or cron jobs.
- **`streamlit_app.py`** — web dashboard: editable holdings, live charts, CSV export.
- **`test_risk_engine.py`** — unit tests with mocked price data, no network needed.
- **`portfolio.csv`** — your holdings. Add or remove rows freely; nothing is hardcoded.

Separating the engine from the UI is what lets both the CLI and the web app
reuse the exact same, independently-tested logic — one bug fix, two places
it takes effect.

## Setup

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Run the CLI:
```bash
python app.py --portfolio portfolio.csv --benchmark ^NSEI
```

Run the web dashboard locally:
```bash
streamlit run streamlit_app.py
```

Run the tests:
```bash
pytest -v
```

## Deploying the dashboard for free

**Streamlit Community Cloud** (recommended — purpose-built for exactly this):

1. Push this folder to a **public** GitHub repo (private repos work too if you
   sign in with GitHub, but public is simplest for a portfolio piece).
2. Go to **share.streamlit.io** and sign in with GitHub.
3. Click "Create app," pick your repo/branch, and set the main file path to
   `streamlit_app.py`.
4. Deploy. You'll get a live URL like `yourname-portfolio-risk.streamlit.app`
   that updates automatically whenever you push to GitHub.

That's it — no server, no Docker, no credit card. Put the live link at the
top of your GitHub README and in your resume/LinkedIn.

**Alternatives, if you want more "full-stack" surface area for interviews:**
- **Render** or **Railway** free tiers — good if you split this into a FastAPI
  backend + a separate frontend (see "leveling this up" below).
- **Vercel** — great for a React/Next.js frontend, but you'd need the Python
  logic running somewhere else (Render/Railway) since Vercel's free tier isn't
  meant for long-running Python services.
- **GitHub Pages** — static only; won't work here since this needs a live
  Python backend to fetch prices.

## What actually makes a project like this stand out to a fintech recruiter

Being honest: no single side project guarantees an internship — recruiters
weight a lot of things (applications, referrals, interviews, timing). But
this kind of project *is* a genuinely strong signal when it shows more than
"I can write a for-loop that calls an API." A few things that move the needle
more than extra features:

1. **A live, working link.** A deployed app a recruiter can click is worth
   more than a repo they'd have to clone and run.
2. **Correctness under failure.** Handling a bad ticker, an API rate limit,
   or missing data without crashing (already built into `risk_engine.py`)
   signals production thinking, not just a happy-path script.
3. **Tests.** `test_risk_engine.py` mocks the API so it runs offline and
   deterministically — this is exactly what a fintech engineering team
   will ask about in an interview.
4. **You can explain the math.** Be ready to explain, in your own words,
   what Sharpe ratio, VaR, beta, and max drawdown actually mean and why
   each is imperfect (e.g., VaR says nothing about the size of losses
   beyond the threshold). Reviewers probe this in interviews far more
   than they read your code line by line.
5. **A clear README and commit history**, not one giant commit. Small,
   readable commits ("add VaR calculation," "add tests for empty portfolio")
   read as evidence of how you actually work.

## Ideas to extend it further (good for a "future work" section or a v2)

- **Backtesting**: replay the strategy/portfolio over historical data and
  report cumulative returns vs. the benchmark.
- **Multi-currency support**: hold US and Indian stocks together with FX
  conversion (this is a real, non-trivial problem fintech teams deal with).
- **Correlation matrix / sector exposure**: use `yf.Ticker(t).info` to pull
  sector data and flag concentration risk.
- **Alerting**: email/Slack webhook when a position moves beyond a threshold.
- **Persistence**: store daily snapshots in SQLite/Postgres so you can chart
  portfolio value over time instead of just "right now."
- **CI**: add a GitHub Actions workflow that runs `pytest` on every push —
  a small addition that signals real engineering habits.

## Risk metric definitions (quick reference)

| Metric | What it means |
|---|---|
| Volatility (annualized) | How much the portfolio's daily returns swing, scaled to a yearly figure. Higher = more turbulent. |
| Sharpe ratio | Return earned per unit of risk taken, above a risk-free baseline. Higher is generally better; ratios above ~1 are considered decent. |
| Max drawdown | The worst peak-to-trough loss over the period — a "how bad could it have gotten" number. |
| Value at Risk (95%) | The daily loss you'd expect not to exceed 95% of the time. Says nothing about how bad the remaining 5% could be. |
| Beta | Sensitivity to the benchmark. Beta > 1 means the portfolio tends to move more than the market; < 1 means less. |

## Disclaimer

This project is for educational/portfolio purposes. It is not investment
advice, and the risk metrics use simplifying assumptions (e.g., a constant
risk-free rate, normally-behaved returns) that a real trading desk would
not rely on unmodified.
