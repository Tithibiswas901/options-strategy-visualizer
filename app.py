import numpy as np
import streamlit as st
import plotly.graph_objects as go

from pricing import bs_price
from strategies import get_strategy_legs, payoff_at_expiry, pnl_now, net_greeks
from iv_solver import implied_vol

st.set_page_config(page_title="Options Strategy Visualizer", layout="wide")

STRATEGIES = [
    "Long Call",
    "Long Put",
    "Covered Call",
    "Bull Call Spread",
    "Bear Put Spread",
    "Long Straddle",
    "Iron Condor",
]

STRIKE_COUNTS = {
    "Long Call": 1,
    "Long Put": 1,
    "Covered Call": 1,
    "Bull Call Spread": 2,
    "Bear Put Spread": 2,
    "Long Straddle": 1,
    "Iron Condor": 4,
}

STRIKE_LABELS = {
    "Long Call": ["Strike"],
    "Long Put": ["Strike"],
    "Covered Call": ["Call Strike"],
    "Bull Call Spread": ["Lower Strike (buy)", "Upper Strike (sell)"],
    "Bear Put Spread": ["Lower Strike (sell)", "Upper Strike (buy)"],
    "Long Straddle": ["Strike"],
    "Iron Condor": [
        "Put Long Strike (K1)",
        "Put Short Strike (K2)",
        "Call Short Strike (K3)",
        "Call Long Strike (K4)",
    ],
}

DEFAULT_STRIKE_OFFSETS = {
    "Long Call": [5],
    "Long Put": [-5],
    "Covered Call": [5],
    "Bull Call Spread": [-5, 5],
    "Bear Put Spread": [-5, 5],
    "Long Straddle": [0],
    "Iron Condor": [-15, -5, 5, 15],
}


@st.cache_data
def spot_range(spot, num_points=300):
    lo = spot * 0.70
    hi = spot * 1.30
    return np.linspace(lo, hi, num_points)


def sidebar_inputs():
    st.sidebar.header("Strategy Parameters")
    strategy = st.sidebar.selectbox("Strategy", STRATEGIES)

    spot = st.sidebar.number_input("Spot Price (S)", value=100.0, min_value=1.0, step=1.0)
    days = st.sidebar.number_input("Days to Expiry", value=30, min_value=1, max_value=730, step=1)
    iv = st.sidebar.slider("Implied Volatility (%)", min_value=5, max_value=100, value=20, step=1)
    rate = st.sidebar.number_input("Risk-Free Rate (%)", value=5.0, min_value=0.0, max_value=20.0, step=0.1)

    n_strikes = STRIKE_COUNTS[strategy]
    labels = STRIKE_LABELS[strategy]
    offsets = DEFAULT_STRIKE_OFFSETS[strategy]
    strikes = []
    st.sidebar.subheader("Strike Prices")
    for i in range(n_strikes):
        default = round(spot + offsets[i], 2)
        k = st.sidebar.number_input(labels[i], value=float(default), min_value=1.0, step=1.0, key=f"strike_{i}")
        strikes.append(k)

    return strategy, spot, days, iv / 100.0, rate / 100.0, strikes


def metrics_row(legs, S_range, payoff):
    net_cost = sum(leg["quantity"] * leg["premium"] for leg in legs)
    max_profit = float(np.max(payoff))
    max_loss = float(np.min(payoff))

    sign_changes = np.where(np.diff(np.sign(payoff)))[0]
    breakevens = []
    for idx in sign_changes:
        x0, x1 = S_range[idx], S_range[idx + 1]
        y0, y1 = payoff[idx], payoff[idx + 1]
        if y1 != y0:
            be = x0 - y0 * (x1 - x0) / (y1 - y0)
            breakevens.append(round(be, 2))

    col1, col2, col3, col4 = st.columns(4)
    cost_label = "Strategy Cost" if net_cost >= 0 else "Strategy Credit"
    col1.metric(cost_label, f"${abs(net_cost):.2f}")
    col2.metric("Max Profit", f"${max_profit:.2f}" if max_profit < 1e9 else "Unlimited")
    col3.metric("Max Loss", f"${max_loss:.2f}" if max_loss > -1e9 else "Unlimited")
    col4.metric(
        "Breakeven(s)",
        ", ".join(f"${b}" for b in breakevens) if breakevens else "N/A",
    )
    return net_cost


def greeks_table(legs, spot, T, r, sigma):
    g = net_greeks(legs, spot, T, r, sigma)
    cols = st.columns(5)
    labels = ["Delta", "Gamma", "Theta ($/day)", "Vega (per 1% vol)", "Rho (per 1% rate)"]
    keys = ["delta", "gamma", "theta", "vega", "rho"]
    for col, label, key in zip(cols, labels, keys):
        col.metric(label, f"{g[key]:.4f}")


def payoff_chart(S_range, payoff, current_pnl, spot):
    fig = go.Figure()

    # Shaded profit region (expiry)
    profit_mask = payoff >= 0
    loss_mask = payoff < 0

    # Green fill for profit
    fig.add_trace(
        go.Scatter(
            x=np.concatenate([S_range[profit_mask], S_range[profit_mask][::-1]]),
            y=np.concatenate([payoff[profit_mask], np.zeros(profit_mask.sum())]),
            fill="toself",
            fillcolor="rgba(0,200,80,0.15)",
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip",
        )
    )

    # Red fill for loss
    fig.add_trace(
        go.Scatter(
            x=np.concatenate([S_range[loss_mask], S_range[loss_mask][::-1]]),
            y=np.concatenate([payoff[loss_mask], np.zeros(loss_mask.sum())]),
            fill="toself",
            fillcolor="rgba(220,50,50,0.15)",
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip",
        )
    )

    # Payoff at expiry
    fig.add_trace(
        go.Scatter(
            x=S_range,
            y=payoff,
            mode="lines",
            name="Payoff at Expiry",
            line=dict(color="#00c851", width=2.5),
        )
    )

    # Current P&L
    fig.add_trace(
        go.Scatter(
            x=S_range,
            y=current_pnl,
            mode="lines",
            name="Current P&L",
            line=dict(color="#4d90fe", width=2, dash="dash"),
        )
    )

    # Zero line
    fig.add_hline(y=0, line=dict(color="white", width=1, dash="dot"))

    # Spot line
    fig.add_vline(x=spot, line=dict(color="orange", width=1.5, dash="dash"),
                  annotation_text=f"Spot ${spot:.0f}", annotation_position="top right")

    fig.update_layout(
        title="Options Strategy P&L",
        xaxis_title="Spot Price at Expiry ($)",
        yaxis_title="P&L ($)",
        template="plotly_dark",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=50, r=30, t=60, b=50),
        height=480,
    )
    return fig


def iv_calculator_section():
    with st.expander("Implied Volatility Calculator"):
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        iv_spot = c1.number_input("Spot (S)", value=100.0, min_value=0.01, key="iv_s")
        iv_strike = c2.number_input("Strike (K)", value=100.0, min_value=0.01, key="iv_k")
        iv_days = c3.number_input("Days to Expiry", value=30, min_value=1, key="iv_days")
        iv_rate = c4.number_input("Rate (%)", value=5.0, key="iv_rate") / 100.0
        iv_type = c5.selectbox("Type", ["call", "put"], key="iv_type")
        iv_market = c6.number_input("Market Price", value=3.00, min_value=0.0, key="iv_mkt")

        if st.button("Calculate IV"):
            T_iv = iv_days / 365.0
            result = implied_vol(iv_market, iv_spot, iv_strike, T_iv, iv_rate, iv_type)
            if result is None:
                st.error("IV solver did not converge. Check inputs.")
            else:
                st.success(f"Implied Volatility: **{result * 100:.2f}%**")


def main():
    st.title("Options Strategy Visualizer")

    strategy, spot, days, sigma, r, strikes = sidebar_inputs()
    T = days / 365.0

    legs = get_strategy_legs(strategy, spot, strikes, T, r, sigma)
    S_range = spot_range(spot)

    payoff = payoff_at_expiry(legs, S_range)

    st.subheader("Position Summary")
    metrics_row(legs, S_range, payoff)

    st.subheader("Net Greeks")
    greeks_table(legs, spot, T, r, sigma)

    # Days-to-expiry slider for morphing P&L curve
    days_remaining = st.slider(
        "Days to Expiry (drag to watch P&L evolve)",
        min_value=0,
        max_value=int(days),
        value=int(days),
        step=1,
    )
    T_remaining = max(days_remaining / 365.0, 1e-6)

    current_pnl = pnl_now(legs, S_range, T_remaining, r, sigma)

    fig = payoff_chart(S_range, payoff, current_pnl, spot)
    st.plotly_chart(fig, use_container_width=True)

    iv_calculator_section()


if __name__ == "__main__":
    main()
