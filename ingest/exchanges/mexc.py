"""
MEXC.

MEXC copies Binance's API design, so the field names match Binance.
The list comes back directly.
"""

from ingest.base import Exchange


class MEXC(Exchange):
    SLUG = "mexc"
    NAME = "MEXC"
    URL = "https://api.mexc.com/api/v3/ticker/24hr"
    FIELDS = {
        "symbol": "symbol",        # e.g. BTCUSDT
        "price": "lastPrice",
        "bid": "bidPrice",
        "ask": "askPrice",
        "high_24h": "highPrice",
        "low_24h": "lowPrice",
        "volume_24h": "volume",
    }
