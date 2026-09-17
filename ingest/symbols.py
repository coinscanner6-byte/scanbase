"""
Turning each exchange's symbol naming into one standard form.

The problem this solves:
    Binance calls Bitcoin/USDT   "BTCUSDT"
    OKX     calls it             "BTC-USDT"
    Gate.io calls it             "BTC_USDT"
    MEXC    calls it             "BTCUSDT"
    Bybit   calls it             "BTCUSDT"

All five mean the same thing. Without standardising, a customer asking
for Bitcoin only gets some of the exchanges back.

We convert everything to one form: BASE-QUOTE, e.g. "BTC-USDT".
We always keep the exchange's original spelling too, so we can trace
any row back to exactly what the exchange sent us.
"""

# The quote currency is the second half of a pair - the thing you're
# pricing IN. "BTCUSDT" means Bitcoin priced in USDT.
#
# Order matters here: longer ones must come first. If we checked "USD"
# before "USDT", then "BTCUSDT" would wrongly split into BTC + USD with
# a leftover "T".
KNOWN_QUOTES = [
    "USDT", "USDC", "TUSD", "BUSD", "FDUSD",
    "USD", "EUR", "GBP", "TRY", "BRL", "INR", "JPY",
    "BTC", "ETH", "BNB", "SOL",
]


def standardise(raw_symbol):
    """
    Takes whatever an exchange called a pair and returns our standard
    form, e.g.:
        "BTCUSDT"   -> "BTC-USDT"
        "BTC-USDT"  -> "BTC-USDT"
        "BTC_USDT"  -> "BTC-USDT"

    If we genuinely can't work out how to split it, we return the
    symbol uppercased and unchanged rather than guessing. Better to
    leave one symbol unmatched than to mangle it into something wrong.
    """
    if not raw_symbol:
        return None

    symbol = raw_symbol.strip().upper()

    # Easy case: the exchange already used a separator, so we just
    # normalise which separator it is.
    if "-" in symbol:
        return symbol.replace("-", "-", 1)
    if "_" in symbol:
        return symbol.replace("_", "-", 1)
    if "/" in symbol:
        return symbol.replace("/", "-", 1)

    # Harder case: no separator at all, e.g. "BTCUSDT". We have to work
    # out where the split belongs by checking known quote currencies.
    for quote in KNOWN_QUOTES:
        if symbol.endswith(quote) and len(symbol) > len(quote):
            base = symbol[: -len(quote)]
            return f"{base}-{quote}"

    # Couldn't work it out - return unchanged rather than guessing wrong.
    return symbol
