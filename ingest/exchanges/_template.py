"""
TEMPLATE - copy this file to add a new exchange.

1. Copy to a new name without the underscore, e.g. kucoin.py
2. Fill in SLUG, NAME, URL and FIELDS (their names on the right)
3. If their list is wrapped inside other keys, fill in extract()
4. Add the exchange to the database:
       INSERT INTO exchanges (slug, name) VALUES ('kucoin', 'KuCoin');
5. Test it alone:  python3 -m scripts.run_once kucoin

Files starting with "_" are ignored by the worker, so this template
never runs by itself.
"""

from ingest.base import Exchange


class NewExchange(Exchange):
    SLUG = "newexchange"
    NAME = "New Exchange"
    URL = "https://api.example.com/tickers"
    FIELDS = {
        "symbol": "their_symbol_name",
        "price": "their_price_name",
        # "bid": "...", "ask": "...", "high_24h": "...",
        # "low_24h": "...", "volume_24h": "...",
    }

    # ONLY_QUOTES = ("INR",)     # keep only INR pairs

    # def extract(self, data):
    #     return data["result"]["list"]

    # def adjust(self, row, item):
    #     # fix values here; return None to skip the pair
    #     return row
