"""
ZebPay (India).

The list sits inside "data". ZebPay fills fields it doesn't track
with "0" or "" - we store those as empty rather than as a real zero.
"""

from ingest.base import Exchange
from ingest.exchanges._helpers import zero_to_none


class ZebPay(Exchange):
    SLUG = "zebpay"
    NAME = "ZebPay"
    URL = "https://sapi.zebpay.com/api/v2/market/allTickers"
    FIELDS = {
        "symbol": "symbol",        # e.g. BTC-INR
        "price": "last",
        "bid": "bid",
        "ask": "ask",
        "high_24h": "high",
        "low_24h": "low",
        "volume_24h": "baseVolume",
        "exchange_time": "timestamp",
    }

    def extract(self, data):
        return data.get("data") or []

    def adjust(self, row, item):
        return zero_to_none(row, ("bid", "ask", "high_24h", "low_24h", "volume_24h"))
