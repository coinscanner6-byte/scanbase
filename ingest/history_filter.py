"""
Decides which pairs are worth keeping in permanent hourly history.

Every exchange lists thousands of pairs, and most are dead: almost no
trading, often junk tokens. Saving all of them every hour made the
history table grow by an estimated 1-2 GB a month for data nobody uses.

Rule:
  1. The pair must be priced in a currency we care about (USDT/USDC/INR).
  2. INR pairs are always kept.
  3. USDT/USDC pairs must have real trading in the last 24 hours.

Live prices are NOT affected - every pair still appears in /v1/ticker.
"""

from shared.config import HISTORY_QUOTES, HISTORY_ALWAYS_KEEP_QUOTES, MIN_HISTORY_VOLUME_USD


def quote_of(symbol_std):
    """'BTC-USDT' -> 'USDT'. Returns None if the symbol couldn't be split."""
    if not symbol_std or "-" not in symbol_std:
        return None
    return symbol_std.rsplit("-", 1)[1]


def keep_in_history(row):
    quote = quote_of(row.get("symbol_std"))
    if quote not in HISTORY_QUOTES:
        return False
    if quote in HISTORY_ALWAYS_KEEP_QUOTES:
        return True

    volume = row.get("volume_24h")
    if volume is None:
        # Exchange didn't tell us - keep it rather than lose a real pair.
        return True

    # volume_24h is counted in the coin itself (e.g. 1,234 BTC), so
    # price x volume gives roughly the dollars traded.
    return row["price"] * volume >= MIN_HISTORY_VOLUME_USD


def filter_for_history(rows):
    return [r for r in rows if keep_in_history(r)]
