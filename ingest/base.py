"""
The template every exchange follows.

Think of this as a standard form. Every exchange sends prices in its
own shape with its own names ("lastPrice", "last", "instId"...). An
exchange file only fills in the blanks on this form:

    SLUG        our short code for it, e.g. "binance"
    NAME        display name, e.g. "Binance"
    URL         where to ask for prices
    FIELDS      which of THEIR names means which of OUR names
    extract()   (only if needed) where the list sits inside their reply

Everything else - calling the exchange, handling timeouts, translating
names into our standard shape - is done here, once, for all of them.

To add a new exchange: copy any file in ingest/exchanges/, change the
blanks, and add one row to the exchanges table. The worker finds the
new file by itself. Nothing else needs to change.
"""

import httpx

from shared.config import DEFAULT_TIMEOUT_SECONDS
from ingest.symbols import standardise

# Our standard names. Every exchange gets translated into exactly these.
STANDARD_FIELDS = ("symbol", "price", "bid", "ask", "high_24h", "low_24h", "volume_24h",
                   "exchange_time")


class Exchange:
    SLUG = None
    NAME = None
    URL = None
    TIMEOUT = DEFAULT_TIMEOUT_SECONDS

    # Map of OUR name -> THEIR name. "symbol" and "price" are required.
    FIELDS = {}

    # If set, only pairs priced in these currencies are kept, e.g. ("INR",).
    # Used when an exchange's other pairs just copy another exchange.
    ONLY_QUOTES = None

    def extract(self, data):
        """
        Returns the list of tickers from the exchange's reply. Most
        exchanges send the list directly; ones that wrap it inside
        other keys override this.
        """
        return data

    def adjust(self, row, item):
        """
        Optional per-exchange fix-up after the fields are translated.
        'row' is our standard dict, 'item' is the exchange's original.
        Return the (changed) row, or None to skip this pair.
        """
        return row

    # Some exchanges refuse requests with no browser-style name.
    HEADERS = {"User-Agent": "Mozilla/5.0 (Scanbase market data)", "Accept": "application/json"}

    def fetch_raw(self):
        """Makes the actual internet call. Kept separate so tests can skip it."""
        response = httpx.get(self.URL, timeout=self.TIMEOUT, headers=self.HEADERS,
                             follow_redirects=True)
        response.raise_for_status()
        return response.json()

    def parse(self, data):
        """Turns the exchange's reply into a list of dicts in our standard shape."""
        rows = []
        for item in self.extract(data) or []:
            if not isinstance(item, dict):
                continue
            row = {ours: item.get(theirs) for ours, theirs in self.FIELDS.items()}
            row = self.adjust(row, item)
            if row is None:
                continue
            if self.ONLY_QUOTES:
                std = standardise(row.get("symbol") or "")
                if not std or std.rsplit("-", 1)[-1] not in self.ONLY_QUOTES:
                    continue
            rows.append(row)
        return rows

    def fetch(self):
        return self.parse(self.fetch_raw())

    @classmethod
    def check_setup(cls):
        """Catches a badly filled-in exchange file at startup, not at 3am."""
        missing = [k for k in ("SLUG", "NAME", "URL") if not getattr(cls, k)]
        if missing:
            raise ValueError(f"{cls.__name__} is missing: {', '.join(missing)}")
        for required in ("symbol", "price"):
            if required not in cls.FIELDS:
                raise ValueError(f"{cls.__name__}.FIELDS must include '{required}'")
        unknown = set(cls.FIELDS) - set(STANDARD_FIELDS)
        if unknown:
            raise ValueError(f"{cls.__name__}.FIELDS has unknown names: {unknown}")
