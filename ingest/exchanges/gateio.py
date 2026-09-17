"""
Gate.io.

Gate.io calls the pair "currency_pair" and the price "last".
The list comes back directly.
"""

from ingest.base import Exchange


class GateIO(Exchange):
    SLUG = "gateio"
    NAME = "Gate.io"
    URL = "https://api.gateio.ws/api/v4/spot/tickers"
    TIMEOUT = 10
    FIELDS = {
        "symbol": "currency_pair",  # e.g. BTC_USDT
        "price": "last",
        "bid": "highest_bid",
        "ask": "lowest_ask",
        "high_24h": "high_24h",
        "low_24h": "low_24h",
        "volume_24h": "base_volume",
    }
