"""
CoinDCX (India).

Only INR pairs are collected. CoinDCX's USDT pairs mirror Binance -
their 24h volume matches Binance's exactly - so collecting them would
count Binance twice.

CoinDCX reports volume in the QUOTE currency (rupees traded), so we
divide by price to get the amount of the coin itself, like every other
exchange.
"""

from ingest.base import Exchange
from ingest.exchanges._helpers import to_float


class CoinDCX(Exchange):
    SLUG = "coindcx"
    NAME = "CoinDCX"
    URL = "https://api.coindcx.com/exchange/ticker"
    ONLY_QUOTES = ("INR",)
    FIELDS = {
        "symbol": "market",        # e.g. BTCINR
        "price": "last_price",
        "bid": "bid",
        "ask": "ask",
        "high_24h": "high",
        "low_24h": "low",
        "volume_24h": "volume",
    }

    def adjust(self, row, item):
        price = to_float(row["price"])
        quote_volume = to_float(row["volume_24h"])
        row["volume_24h"] = quote_volume / price if price and quote_volume else None
        return row
