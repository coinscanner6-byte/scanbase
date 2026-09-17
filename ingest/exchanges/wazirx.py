"""
WazirX (India).

Symbols come lowercase with no separator ("btcinr"), but WazirX also
sends baseAsset/quoteAsset, so we build "BTC-INR" from those - safer
than guessing where to split.
"""

from ingest.base import Exchange


class WazirX(Exchange):
    SLUG = "wazirx"
    NAME = "WazirX"
    URL = "https://api.wazirx.com/sapi/v1/tickers/24hr"
    FIELDS = {
        "symbol": "symbol",
        "price": "lastPrice",
        "bid": "bidPrice",
        "ask": "askPrice",
        "high_24h": "highPrice",
        "low_24h": "lowPrice",
        "volume_24h": "volume",
    }

    def adjust(self, row, item):
        base, quote = item.get("baseAsset"), item.get("quoteAsset")
        if base and quote:
            row["symbol"] = f"{base}-{quote}".upper()
        return row
