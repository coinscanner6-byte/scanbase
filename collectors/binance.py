"""
This file knows how to talk to Binance, and nothing else.
If Binance changes their API tomorrow, this is the only file
that needs fixing.

Note: we switched from the simple "ticker/price" endpoint to the
"ticker/24hr" endpoint, because the simple one only ever sends the
price - no bid, ask, or volume. The 24hr endpoint gives us all of it
in one call.
"""

import httpx

URL = "https://data-api.binance.vision/api/v3/ticker/24hr"


def fetch():
    """
    Ask Binance for full 24-hour stats on every pair. Returns a list of
    {"symbol": ..., "price": ..., "bid": ..., "ask": ..., "high_24h": ...,
    "low_24h": ..., "volume_24h": ...} dicts in our own plain format.
    """
    response = httpx.get(URL, timeout=15)
    response.raise_for_status()
    data = response.json()

    return [
        {
            "symbol": item["symbol"],
            "price": item["lastPrice"],
            "bid": item.get("bidPrice"),
            "ask": item.get("askPrice"),
            "high_24h": item.get("highPrice"),
            "low_24h": item.get("lowPrice"),
            "volume_24h": item.get("volume"),
        }
        for item in data
    ]

