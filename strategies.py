import numpy as np
from pricing import bs_price, delta, gamma, theta, vega, rho


def _leg(option_type, strike, quantity, premium):
    return {
        "type": option_type,
        "strike": strike,
        "quantity": quantity,
        "premium": premium,
    }


def get_strategy_legs(strategy_name, spot, strikes, T, r, sigma):
    """
    strikes: list of strike prices (length depends on strategy).
    Returns list of leg dicts.
    """
    s = strategy_name

    if s == "Long Call":
        K = strikes[0]
        p = bs_price(spot, K, T, r, sigma, "call")
        return [_leg("call", K, 1, p)]

    if s == "Long Put":
        K = strikes[0]
        p = bs_price(spot, K, T, r, sigma, "put")
        return [_leg("put", K, 1, p)]

    if s == "Covered Call":
        K = strikes[0]
        call_p = bs_price(spot, K, T, r, sigma, "call")
        return [
            _leg("stock", spot, 1, spot),
            _leg("call", K, -1, call_p),
        ]

    if s == "Bull Call Spread":
        K1, K2 = sorted(strikes[:2])
        p1 = bs_price(spot, K1, T, r, sigma, "call")
        p2 = bs_price(spot, K2, T, r, sigma, "call")
        return [_leg("call", K1, 1, p1), _leg("call", K2, -1, p2)]

    if s == "Bear Put Spread":
        K1, K2 = sorted(strikes[:2])
        # long higher put, short lower put
        p_high = bs_price(spot, K2, T, r, sigma, "put")
        p_low = bs_price(spot, K1, T, r, sigma, "put")
        return [_leg("put", K2, 1, p_high), _leg("put", K1, -1, p_low)]

    if s == "Long Straddle":
        K = strikes[0]
        call_p = bs_price(spot, K, T, r, sigma, "call")
        put_p = bs_price(spot, K, T, r, sigma, "put")
        return [_leg("call", K, 1, call_p), _leg("put", K, 1, put_p)]

    if s == "Iron Condor":
        # strikes: [K1_put_long, K2_put_short, K3_call_short, K4_call_long]
        K1, K2, K3, K4 = sorted(strikes[:4])
        p1 = bs_price(spot, K1, T, r, sigma, "put")
        p2 = bs_price(spot, K2, T, r, sigma, "put")
        p3 = bs_price(spot, K3, T, r, sigma, "call")
        p4 = bs_price(spot, K4, T, r, sigma, "call")
        return [
            _leg("put", K1, 1, p1),
            _leg("put", K2, -1, p2),
            _leg("call", K3, -1, p3),
            _leg("call", K4, 1, p4),
        ]

    raise ValueError(f"Unknown strategy: {s}")


def payoff_at_expiry(legs, S_range):
    """Returns net P&L at expiry for each spot in S_range."""
    total = np.zeros(len(S_range))
    net_cost = sum(leg["quantity"] * leg["premium"] for leg in legs)

    for leg in legs:
        q = leg["quantity"]
        K = leg["strike"]
        t = leg["type"]
        if t == "call":
            intrinsic = np.maximum(S_range - K, 0.0)
        elif t == "put":
            intrinsic = np.maximum(K - S_range, 0.0)
        else:
            # stock: payoff relative to entry price
            intrinsic = S_range - K
        total += q * intrinsic

    return total - net_cost


def pnl_now(legs, S_range, T_remaining, r, sigma):
    """Current P&L by re-valuing each leg at T_remaining."""
    net_cost = sum(leg["quantity"] * leg["premium"] for leg in legs)
    total = np.zeros(len(S_range))

    for leg in legs:
        q = leg["quantity"]
        K = leg["strike"]
        t = leg["type"]
        if t == "stock":
            current_values = S_range - K
        else:
            current_values = np.array(
                [bs_price(float(s), K, T_remaining, r, sigma, t) for s in S_range]
            )
        total += q * current_values

    return total - net_cost


def net_greeks(legs, spot, T, r, sigma):
    """Returns dict of summed Greeks weighted by quantity."""
    result = {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0, "rho": 0.0}
    for leg in legs:
        q = leg["quantity"]
        K = leg["strike"]
        t = leg["type"]
        if t == "stock":
            result["delta"] += q * 1.0
            continue
        result["delta"] += q * delta(spot, K, T, r, sigma, t)
        result["gamma"] += q * gamma(spot, K, T, r, sigma)
        result["theta"] += q * theta(spot, K, T, r, sigma, t)
        result["vega"] += q * vega(spot, K, T, r, sigma)
        result["rho"] += q * rho(spot, K, T, r, sigma, t)
    return result
