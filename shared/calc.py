"""
Small market calculations with no database and no internet, so they
can be tested on their own and run anywhere.
"""

# How far back each change window looks, in hours.
CHANGE_WINDOWS = {"change_1h": 1, "change_24h": 24, "change_7d": 24 * 7}


def market_cap(base, price, supplies):
    """
    Price x circulating supply - the usual way every market list is
    ordered. Returns None when we do not know the supply, because an
    invented market cap is worse than an empty one.
    """
    supply = (supplies or {}).get(base)
    if not supply or not price:
        return None
    return round(price * supply, 2)
