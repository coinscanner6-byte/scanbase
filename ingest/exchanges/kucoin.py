"""
KuCoin (global) - an affiliate partner.

The list sits two levels deep: {"data": {"ticker": [...]}}.
KuCoin calls best bid "buy" and best ask "sell".
"""

from ingest.base import Exchange


class KuCoin(Exchange):
    SLUG = "kucoin"
    NAME = "KuCoin"
    URL = "https://api.kucoin.com/api/v1/market/allTickers"
    TIMEOUT = 20
    FIELDS = {
        "symbol": "symbol",        # e.g. BTC-USDT
        "price": "last",
        "bid": "buy",
        "ask": "sell",
        "high_24h": "high",
        "low_24h": "low",
        "volume_24h": "vol",
    }

    def extract(self, data):
        return (data.get("data") or {}).get("ticker") or []
