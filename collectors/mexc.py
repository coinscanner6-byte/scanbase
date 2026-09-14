"""
This file knows how to talk to MEXC, and nothing else.
If MEXC changes their API tomorrow, this is the only file
that needs fixing.

MEXC's shape is close to Binance's - a flat list with "symbol"
and "price" already named the same way we want them.
"""

import httpx

URL = "https://api.mexc.com/api/v3/ticker/price"


def fetch():
    """
    Ask MEXC for every current price. Returns a list of
    {"symbol": ..., "price": ...} dicts in our own plain format.
    """
    response = httpx.get(URL, timeout=10)
    response.raise_for_status()
    data = response.json()

    return [{"symbol": item["symbol"], "price": item["price"]} for item in data]
