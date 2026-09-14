"""
This file knows how to talk to MEXC, and nothing else.
If MEXC changes their API tomorrow, this is the only file
that needs fixing.

MEXC's API is designed to closely copy Binance's, including this
24hr endpoint and field names. This is a reasonable assumption based
on how MEXC documents itself, but unlike our other collectors, this
specific endpoint has not been tested against MEXC's real response -
only the simpler price-only endpoint was confirmed back in stage 0.
Check the very first real run of this file carefully.
"""

import httpx

URL = "https://api.mexc.com/api/v3/ticker/24hr"


def fetch():
    """
    Ask MEXC for full 24-hour stats on every pair. Returns a list of
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

