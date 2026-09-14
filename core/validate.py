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


def to_number_or_none(value):
    """
    Converts a value to a real number if possible, or returns None if
    it's missing or broken. Used for the extra fields (bid, ask, etc)
    where we'd rather save the row without them than throw the whole
    row away over one missing field.
    """
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def clean_prices(raw_prices):
    """
    Takes a list of price dicts and returns only the ones that pass
    validation, with every number converted to a real number.

    The main "price" field is required and strictly checked - a bad
    price means we throw the whole row away. The extra fields (bid,
    ask, 24h high/low, volume) are optional - if an exchange didn't
    send one, or sent something broken, we save the row anyway with
    that one field empty rather than losing the price over it.
    """
    good = []
    for item in raw_prices:
        symbol = item.get("symbol")
        price = item.get("price")

        if not symbol:
            continue
        if not is_valid_price(symbol, price):
            continue

        good.append({
            "symbol": symbol,
            "price": float(price),
            "bid": to_number_or_none(item.get("bid")),
            "ask": to_number_or_none(item.get("ask")),
            "high_24h": to_number_or_none(item.get("high_24h")),
            "low_24h": to_number_or_none(item.get("low_24h")),
            "volume_24h": to_number_or_none(item.get("volume_24h")),
        })

    return good
