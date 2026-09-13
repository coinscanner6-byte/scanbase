"""
This file knows how to talk to OKX, and nothing else.
If OKX changes their API tomorrow, this is the only file
that needs fixing.

OKX sends its data in a different shape than Binance:
    {"code": "0", "data": [{"instId": "BTC-USDT", "last": "65000.5", ...}]}

Binance calls the coin pair "symbol" and the price "price".
OKX calls them "instId" and "last". This file's whole job is
translating OKX's names into our own standard names, so the rest
of the program never has to know OKX exists.
"""

import httpx

URL = "https://www.okx.com/api/v5/market/tickers?instType=SPOT"


def fetch():
    """
    Ask OKX for every current spot price. Returns a list of
    {"symbol": ..., "price": ...} dicts in our own plain format,
    the same shape every other collector returns, regardless of
    how different OKX's original reply looks.
    """
    response = httpx.get(URL, timeout=10)
    response.raise_for_status()
    data = response.json()

    # OKX wraps its real data one level deeper, inside a "data" key
    tickers = data.get("data", [])

    return [
        {"symbol": item["instId"], "price": item["last"]}
        for item in tickers
    ]
