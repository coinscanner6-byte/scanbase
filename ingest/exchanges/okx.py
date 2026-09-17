"""
OKX.

OKX wraps its list inside a "data" key:
    {"code": "0", "data": [{"instId": "BTC-USDT", "last": "65000.5"}]}
"""

from ingest.base import Exchange


class OKX(Exchange):
    SLUG = "okx"
    NAME = "OKX"
    URL = "https://www.okx.com/api/v5/market/tickers?instType=SPOT"
    TIMEOUT = 10
    FIELDS = {
        "symbol": "instId",        # e.g. BTC-USDT
        "price": "last",
        "bid": "bidPx",
        "ask": "askPx",
        "high_24h": "high24h",
        "low_24h": "low24h",
        "volume_24h": "vol24h",
    }

    def extract(self, data):
        return data.get("data", [])
