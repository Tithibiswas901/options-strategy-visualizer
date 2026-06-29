import sys
import os
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from strategies import get_strategy_legs, payoff_at_expiry, pnl_now
from iv_solver import implied_vol
from pricing import bs_price


S, K1, K2, T, r, sigma = 100.0, 95.0, 105.0, 0.25, 0.05, 0.20


def test_bull_call_spread_max_profit():
    legs = get_strategy_legs("Bull Call Spread", S, [K1, K2], T, r, sigma)
    S_range = np.linspace(80, 130, 500)
    payoff = payoff_at_expiry(legs, S_range)

    expected_max = K2 - K1 - sum(leg["quantity"] * leg["premium"] for leg in legs)
    actual_max = float(np.max(payoff))
    assert abs(actual_max - expected_max) < 0.01, (
        f"Bull spread max profit: expected {expected_max:.4f}, got {actual_max:.4f}"
    )


def test_bull_call_spread_max_loss():
    legs = get_strategy_legs("Bull Call Spread", S, [K1, K2], T, r, sigma)
    S_range = np.linspace(80, 130, 500)
    payoff = payoff_at_expiry(legs, S_range)
    net_debit = sum(leg["quantity"] * leg["premium"] for leg in legs)
    # max loss = net debit paid (when spot << K1)
    assert float(np.min(payoff)) < 0
    assert abs(float(payoff[0]) - (-net_debit)) < 0.01


def test_long_straddle_shape():
    """Straddle should have V-shape: profits on large moves, loss near strike."""
    K = 100.0
    legs = get_strategy_legs("Long Straddle", S, [K], T, r, sigma)
    S_range = np.linspace(60, 140, 500)
    payoff = payoff_at_expiry(legs, S_range)
    # Center should be the minimum (loss zone)
    center_idx = np.argmin(np.abs(S_range - K))
    assert payoff[center_idx] == payoff.min() or payoff[center_idx] < 0
    # Extremes should profit
    assert payoff[0] > payoff[center_idx]
    assert payoff[-1] > payoff[center_idx]


def test_long_call_payoff():
    K = 100.0
    legs = get_strategy_legs("Long Call", S, [K], T, r, sigma)
    S_range = np.array([90.0, 100.0, 110.0, 120.0])
    payoff = payoff_at_expiry(legs, S_range)
    premium = legs[0]["premium"]
    expected = np.array([
        -premium,
        -premium,
        10.0 - premium,
        20.0 - premium,
    ])
    np.testing.assert_allclose(payoff, expected, atol=1e-9)


def test_long_put_payoff():
    K = 100.0
    legs = get_strategy_legs("Long Put", S, [K], T, r, sigma)
    S_range = np.array([80.0, 90.0, 100.0, 110.0])
    payoff = payoff_at_expiry(legs, S_range)
    premium = legs[0]["premium"]
    expected = np.array([
        20.0 - premium,
        10.0 - premium,
        -premium,
        -premium,
    ])
    np.testing.assert_allclose(payoff, expected, atol=1e-9)


def test_pnl_now_at_T_equals_expiry():
    """At T_remaining ~0, pnl_now should approximate payoff_at_expiry."""
    K = 100.0
    legs = get_strategy_legs("Long Call", S, [K], T, r, sigma)
    S_range = np.linspace(80, 130, 100)
    payoff = payoff_at_expiry(legs, S_range)
    current = pnl_now(legs, S_range, 1e-6, r, sigma)
    np.testing.assert_allclose(current, payoff, atol=0.10)


def test_iv_solver_roundtrip():
    """Price an option then recover sigma within 1e-4."""
    true_sigma = 0.25
    price = bs_price(100.0, 100.0, 0.5, 0.05, true_sigma, "call")
    recovered = implied_vol(price, 100.0, 100.0, 0.5, 0.05, "call")
    assert recovered is not None, "IV solver did not converge"
    assert abs(recovered - true_sigma) < 1e-4, (
        f"IV roundtrip: expected {true_sigma}, got {recovered}"
    )


def test_iv_solver_put_roundtrip():
    true_sigma = 0.30
    price = bs_price(100.0, 105.0, 0.25, 0.05, true_sigma, "put")
    recovered = implied_vol(price, 100.0, 105.0, 0.25, 0.05, "put")
    assert recovered is not None
    assert abs(recovered - true_sigma) < 1e-4
