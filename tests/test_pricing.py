import math
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pricing import bs_price, delta, gamma, theta, vega, rho


# Hull's example: S=42, K=40, T=0.5, r=0.10, sigma=0.20
S, K, T, r, sigma = 42.0, 40.0, 0.5, 0.10, 0.20


def test_call_price_hull():
    price = bs_price(S, K, T, r, sigma, "call")
    assert abs(price - 4.76) < 0.01, f"Expected ~4.76, got {price:.4f}"


def test_put_price_hull():
    price = bs_price(S, K, T, r, sigma, "put")
    assert abs(price - 0.81) < 0.01, f"Expected ~0.81, got {price:.4f}"


def test_put_call_parity():
    call = bs_price(S, K, T, r, sigma, "call")
    put = bs_price(S, K, T, r, sigma, "put")
    lhs = call - put
    rhs = S - K * math.exp(-r * T)
    assert abs(lhs - rhs) < 1e-6, f"Put-call parity failed: {lhs} != {rhs}"


def test_call_delta_positive():
    d = delta(S, K, T, r, sigma, "call")
    assert 0 < d < 1, f"Call delta should be in (0,1), got {d}"


def test_put_delta_negative():
    d = delta(S, K, T, r, sigma, "put")
    assert -1 < d < 0, f"Put delta should be in (-1,0), got {d}"


def test_gamma_positive():
    g_call = gamma(S, K, T, r, sigma)
    assert g_call > 0, "Gamma must be positive"


def test_theta_negative_long_options():
    tc = theta(S, K, T, r, sigma, "call")
    tp = theta(S, K, T, r, sigma, "put")
    assert tc < 0, f"Long call theta must be negative, got {tc}"
    assert tp < 0, f"Long put theta must be negative, got {tp}"


def test_vega_positive():
    v = vega(S, K, T, r, sigma)
    assert v > 0, "Vega must be positive"


def test_edge_T_zero():
    call = bs_price(100, 95, 0, 0.05, 0.20, "call")
    assert abs(call - 5.0) < 1e-9
    put = bs_price(100, 105, 0, 0.05, 0.20, "put")
    assert abs(put - 5.0) < 1e-9


def test_edge_sigma_zero():
    # with sigma=0, call intrinsic = max(S - K*exp(-rT), 0)
    import math
    call = bs_price(100, 90, 1.0, 0.05, 0.0, "call")
    expected = max(100 - 90 * math.exp(-0.05), 0.0)
    assert abs(call - expected) < 1e-9
