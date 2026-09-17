"""
Bybit.

Bybit nests its list two levels deep:
    {"result": {"list": [{"symbol": "BTCUSDT", "lastPrice": "65000.5"}]}}
"""

from ingest.base import Exchange


class Bybit(Exchange):
    SLUG = "bybit"
    NAME = "Bybit"
    URL = "https://api.bybit.com/v5/market/tickers?category=spot"
    TIMEOUT = 10
    FIELDS = {
        "symbol": "symbol",        # e.g. BTCUSDT
        "price": "lastPrice",
        "bid": "bid1Price",
        "ask": "ask1Price",
        "high_24h": "highPrice24h",
        "low_24h": "lowPrice24h",
        "volume_24h": "volume24h",
    }

    def extract(self, data):
        return data.get("result", {}).get("list", [])
