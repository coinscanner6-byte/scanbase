"""
The ordinary bank USD-INR rate.

This is NOT a crypto rate. It is the rate a bank or Google would show.
We keep it so we can answer the question an Indian buyer actually has:
how much more am I paying than the plain dollar value of this coin?

The answer is usually a few percent, and almost all of it sits in the
rupee-to-USDT step rather than in the exchange's coin price.
"""

from datetime import datetime, timezone

import httpx
from sqlalchemy import text

from shared.config import FIAT_RATE_URL, DEFAULT_TIMEOUT_SECONDS

# The database is imported inside the functions that need it, so
# fetching and checking a rate can be tested without any database.


def fetch_usd_inr():
    """One call to the free rate service. Returns a number, or None."""
    response = httpx.get(FIAT_RATE_URL, timeout=DEFAULT_TIMEOUT_SECONDS)
    response.raise_for_status()
    rate = (response.json().get("rates") or {}).get("INR")
    rate = float(rate) if rate else None
    # A sane range. Anything outside it means the service changed shape.
    if rate and 50 < rate < 200:
        return rate
    return None


def save_rate(base, quote, rate, source, at=None):
    from storage.db import engine
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO fx_rates (base, quote, rate, source, updated_at)
                VALUES (:b, :q, :r, :s, :at)
                ON CONFLICT (base, quote) DO UPDATE SET
                    rate = EXCLUDED.rate, source = EXCLUDED.source,
                    updated_at = EXCLUDED.updated_at
            """),
            {"b": base, "q": quote, "r": rate, "s": source,
             "at": at or datetime.now(timezone.utc)},
        )


def refresh_usd_inr(log=print):
    """Fetch and store. Never raises - an old rate is better than none."""
    try:
        rate = fetch_usd_inr()
    except Exception as e:
        log(f"  bank USD-INR rate FAILED - {type(e).__name__}: {e}")
        return None
    if not rate:
        log("  bank USD-INR rate: service gave no usable number")
        return None
    save_rate("USD", "INR", rate, "exchangerate-api")
    log(f"  bank USD-INR rate: {rate}")
    return rate


def load_rate(conn, base="USD", quote="INR"):
    row = conn.execute(
        text("SELECT rate, updated_at FROM fx_rates WHERE base = :b AND quote = :q"),
        {"b": base, "q": quote},
    ).first()
    if not row:
        return None, None
    return float(row[0]), row[1]
