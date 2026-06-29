from pricing import bs_price, vega


def implied_vol(market_price, S, K, T, r, option_type, max_iter=50, tol=1e-6):
    if T <= 0:
        return None

    sigma = 0.2
    for _ in range(max_iter):
        price = bs_price(S, K, T, r, sigma, option_type)
        v = vega(S, K, T, r, sigma)
        if abs(v) < 1e-12:
            return None
        # vega() returns per 1% change, so multiply by 100 to get per-unit derivative
        diff = price - market_price
        sigma -= diff / (v * 100.0)
        sigma = max(1e-6, min(sigma, 10.0))
        if abs(diff) < tol:
            return sigma
    return None
