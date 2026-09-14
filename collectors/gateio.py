"""
This file knows how to talk to Gate.io, and nothing else.
If Gate.io changes their API tomorrow, this is the only file
that needs fixing.

Gate.io calls the coin pair "currency_pair" instead of "symbol",
and the price "last" instead of "price". This file translates
that into our own standard shape.
"""

import httpx

URL = "https://api.gateio.ws/api/v4/spot/tickers"


def fetch():
    """
    Ask Gate.io for every current price. Returns a list of
    {"symbol": ..., "price": ...} dicts in our own plain format.
    """
    response = httpx.get(URL, timeout=10)
    response.raise_for_status()
    data = response.json()

    return [
        {
            "symbol": item["currency_pair"],
            "price": item["last"],
            "bid": item.get("highest_bid"),
            "ask": item.get("lowest_ask"),
            "high_24h": item.get("high_24h"),
            "low_24h": item.get("low_24h"),
            "volume_24h": item.get("base_volume"),
        }
        for item in data
    ]
