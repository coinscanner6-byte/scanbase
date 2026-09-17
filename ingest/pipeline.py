"""
One collection round: GET -> CHECK -> STORE, for each exchange.

Both the forever-running worker and the one-off test script use this
same code, so what you test on your Mac is exactly what runs on Railway.
"""

from datetime import datetime, timezone

from ingest.validate import clean_prices
from ingest.history_filter import filter_for_history
from storage.db import get_exchange_id, save_prices, record_success, record_failure

# Exchange ids never change, so we look each one up once and remember it.
_exchange_ids = {}


def _exchange_id(slug):
    if slug not in _exchange_ids:
        _exchange_ids[slug] = get_exchange_id(slug)
    return _exchange_ids[slug]


def run_exchange(exchange):
    """
    Runs one exchange through the full pipeline.
    Returns (fetched, passed, saved, kept_in_history). Raises if something breaks.
    """
    raw = exchange.fetch()                          # GET
    good = clean_prices(raw)                        # CHECK
    collected_at = datetime.now(timezone.utc)
    exchange_id = _exchange_id(exchange.SLUG)
    history = filter_for_history(good)             # which ones to keep forever
    saved = save_prices(exchange_id, good, collected_at, history)   # STORE
    record_success(exchange_id, saved, collected_at)
    return len(raw), len(good), saved, len(history)


def run_round(exchanges, log=print):
    """
    Runs every exchange once. One broken exchange never stops the others.
    Returns {slug: "ok" or error message}.
    """
    results = {}
    for slug, exchange in exchanges.items():
        try:
            fetched, passed, saved, history = run_exchange(exchange)
            log(f"  {slug}: fetched {fetched}, passed {passed}, "
                f"saved {saved} live, {history} to history")
            results[slug] = "ok"
        except Exception as e:
            message = f"{type(e).__name__}: {e}"
            log(f"  {slug}: FAILED - {message}")
            results[slug] = message
            try:
                record_failure(_exchange_id(slug), message, datetime.now(timezone.utc))
            except Exception as inner:
                # Even the database may be down - never let that crash the loop.
                log(f"  {slug}: could not record failure - {inner}")
    return results
