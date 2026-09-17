"""
Binance.

Uses data-api.binance.vision rather than api.binance.com, because the
main domain blocks some regions. The 24hr endpoint gives price, bid,
ask, high, low and volume in one call. The list comes back directly.
"""

from ingest.base import Exchange


class Binance(Exchange):
    SLUG = "binance"
    NAME = "Binance"
    URL = "https://data-api.binance.vision/api/v3/ticker/24hr"
    FIELDS = {
        "symbol": "symbol",        # e.g. BTCUSDT
        "price": "lastPrice",
        "bid": "bidPrice",
        "ask": "askPrice",
        "high_24h": "highPrice",
        "low_24h": "lowPrice",
        "volume_24h": "volume",
    }
