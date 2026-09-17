"""
Giottus (India).

Giottus only sends the best buy offer and best sell offer, no last
trade price:
    {"market": {"BTC/INR": {"top_bid": "7233411 INR", "top_ask": "7819926 INR"}}}

We use the midpoint as the price. When the gap between buy and sell
is wide, the midpoint means little, so those pairs are skipped.
"""

from ingest.base import Exchange
from ingest.exchanges._helpers import to_float

MAX_SPREAD = 0.05   # skip pairs where ask is more than 5% above bid


class Giottus(Exchange):
    SLUG = "giottus"
    NAME = "Giottus"
    URL = "https://www.giottus.com/api/ticker"
    FIELDS = {
        "symbol": "pair",           # e.g. BTC/INR
        "price": "top_bid",         # replaced by the midpoint in adjust()
        "bid": "top_bid",
        "ask": "top_ask",
    }

    def extract(self, data):
        market = data.get("market") or {}
        return [{"pair": pair, **values} for pair, values in market.items()
                if isinstance(values, dict)]

    def adjust(self, row, item):
        bid, ask = to_float(row["bid"]), to_float(row["ask"])
        if not bid or not ask or ask < bid:
            return None
        if (ask - bid) / bid > MAX_SPREAD:
            return None
        row["bid"], row["ask"] = bid, ask
        row["price"] = (bid + ask) / 2
        row["price_source"] = "midpoint"
        return row
