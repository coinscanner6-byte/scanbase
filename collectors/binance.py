"""
This file knows how to talk to Binance, and nothing else.
If Binance changes their API tomorrow, this is the only file
that needs fixing.
"""

import httpx

URL = "https://data-api.binance.vision/api/v3/ticker/price"


def fetch():
    """
    Ask Binance for every current price. Returns a list of
    {"symbol": ..., "price": ...} dicts in our own plain format,
    regardless of what shape Binance originally sent it in.
    """
    response = httpx.get(URL, timeout=10)
    response.raise_for_status()  # raises an error if Binance says something went wrong
    data = response.json()

    # Binance already returns a plain list of {"symbol": ..., "price": ...},
    # so there's not much to convert here - but we still pass it through
    # our own format on purpose, so every collector looks the same to
    # the rest of the program, no matter how different the exchange is.
    return [{"symbol": item["symbol"], "price": item["price"]} for item in data]
