"""
One collection round: GET -> CHECK -> STORE, for each exchange.

Both the forever-running worker and the one-off test script use this
same code, so what you test on your Mac is exactly what runs on Railway.
"""

from datetime import datetime, timezone

from ingest.validate import clean_prices
from ingest.history_filter import filter_for_history
from shared.config import BREAKAGE_DROP
from storage.db import (get_exchange_id, save_prices, record_success,
                        record_failure, record_warning)

# Exchange ids never change, so we look each one up once and remember it.
_exchange_ids = {}

# How many valid pairs each exchange returned last time (this run only).
_last_counts = {}


def _exchange_id(slug):
    if slug not in _exchange_ids:
        _exchange_ids[slug] = get_exchange_id(slug)
    return _exchange_ids[slug]


def exchange_ids():
    return dict(_exchange_ids)


def run_exchange(exchange):
    """
    Runs one exchange through the full pipeline.
    Returns (fetched, passed, saved, kept_in_history, good_rows).
    Raises if something breaks.
    """
    raw = exchange.fetch()                          # GET
    good = clean_prices(raw)                        # CHECK
    collected_at = datetime.now(timezone.utc)
    exchange_id = _exchange_id(exchange.SLUG)

    # An exchange that suddenly returns nothing has almost certainly
    # changed its API - treat it as a failure so it shows as unhealthy.
    if not good:
        raise RuntimeError(f"returned 0 valid prices out of {len(raw)} - API may have changed")

    previous = _last_counts.get(exchange.SLUG)
    if previous and previous >= 20 and len(good) < previous * BREAKAGE_DROP:
        record_warning(
            exchange_id,
            f"only {len(good)} valid pairs, usually about {previous} - API may have changed",
            collected_at,
        )
    _last_counts[exchange.SLUG] = len(good)

    history = filter_for_history(good)             # which ones to keep forever
    saved = save_prices(exchange_id, good, collected_at, history)   # STORE
    record_success(exchange_id, saved, collected_at)
    return len(raw), len(good), saved, len(history), good


def run_round(exchanges, log=print, collect=None):
    """
    Runs every exchange once. One broken exchange never stops the others.
    Returns {slug: "ok" or error message}.
    If 'collect' is a dict, each exchange's cleaned rows are put in it.
    """
    results = {}
    for slug, exchange in exchanges.items():
        try:
            fetched, passed, saved, history, good = run_exchange(exchange)
            if collect is not None:
                collect[slug] = good
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
