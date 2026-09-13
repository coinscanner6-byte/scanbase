"""
This file knows how to talk to Bybit, and nothing else.
If Bybit changes their API tomorrow, this is the only file
that needs fixing.

Bybit nests its data two levels deep:
    {"result": {"list": [{"symbol": "BTCUSDT", "lastPrice": "65000.5", ...}]}}

It also calls the price "lastPrice" instead of "price" or "last".
This file's job is translating that into our own standard shape.
"""

import httpx

URL = "https://api.bybit.com/v5/market/tickers?category=spot"


def fetch():
    """
    Ask Bybit for every current spot price. Returns a list of
    {"symbol": ..., "price": ...} dicts in our own plain format.
    """
    response = httpx.get(URL, timeout=10)
    response.raise_for_status()
    data = response.json()

    # Bybit nests the real list two levels in: result -> list
    tickers = data.get("result", {}).get("list", [])

    return [
        {"symbol": item["symbol"], "price": item["lastPrice"]}
        for item in tickers
    ]
