"""
Before we save anything, we check it isn't obviously broken.
This is deliberately simple for stage 1 - just enough to stop
garbage getting into the database. More checks get added later
(comparing against other exchanges, flagging frozen prices, etc).
"""


def is_valid_price(symbol, price):
    """
    Returns True if this price is worth saving, False if it should
    be thrown away.
    """
    if price is None:
        return False

    try:
        price = float(price)
    except (TypeError, ValueError):
        # The exchange sent something that isn't actually a number
        return False

    if price <= 0:
        # A real coin price is never zero or negative
        return False

    if price > 100_000_000:
        # Sanity ceiling - catches obviously broken responses,
        # like a price sent in the wrong units
        return False

    return True


def clean_prices(raw_prices):
    """
    Takes a list of {"symbol": ..., "price": ...} dicts and returns
    only the ones that pass validation, with price converted to a
    real number.
    """
    good = []
    for item in raw_prices:
        symbol = item.get("symbol")
        price = item.get("price")

        if not symbol:
            continue
        if not is_valid_price(symbol, price):
            continue

        good.append({"symbol": symbol, "price": float(price)})

    return good
