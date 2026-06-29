# Options Strategy Visualizer

An interactive, containerized Streamlit web application for analyzing options trading strategies. Select a strategy (Long Call, Iron Condor, etc.), enter market parameters, and instantly see Black-Scholes pricing, all five Greeks, a payoff diagram at expiry, and a live P&L curve that morphs as days-to-expiry changes — all with no external API dependencies.

![Screenshot](screenshot.png)

## Quick Start

### Run with Docker (recommended)

```bash
docker compose up --build
```

Then open [http://localhost:8501](http://localhost:8501)

### Run locally with Python

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Tests

Tests run locally (not inside the container):

```bash
pytest tests/ -v
```

## Black-Scholes Assumptions

Pricing uses the classic Black-Scholes-Merton model, which assumes: European-style exercise only (no early assignment), no dividends paid by the underlying, constant implied volatility and risk-free rate over the option's life, and log-normally distributed returns.

## Architecture

| Module | Responsibility |
|---|---|
| `pricing.py` | Pure Black-Scholes pricing and Greek calculations (delta, gamma, theta, vega, rho) |
| `strategies.py` | Strategy leg definitions, payoff-at-expiry arrays, and current P&L re-valuation |
| `iv_solver.py` | Newton-Raphson implied volatility solver using vega as the derivative |
| `app.py` | Streamlit UI — sidebar inputs, metrics, Greeks table, Plotly chart, IV calculator |

## Future Work

- **American options**: binomial tree (Cox-Ross-Rubinstein) model to support early exercise
- **Dividend yield**: continuous dividend adjustment in the Black-Scholes formula (`q` parameter)
- **Historical volatility**: EWMA or Parkinson estimator from historical price series to seed the IV slider
