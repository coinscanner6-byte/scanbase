"""
Scanbase worker - runs forever on Railway.

Every round it collects from every exchange, then waits and repeats.
Nobody watches this; it must never crash because of one bad exchange.

Run with:
    python3 -m ingest.worker
"""

import time
from datetime import datetime, timezone

from shared.config import SECONDS_BETWEEN_RUNS, CLEANUP_EVERY_HOURS
from ingest.registry import load_exchanges
from ingest.pipeline import run_round, exchange_ids
from ingest.quality import build_indexes
from storage.db import load_countries, load_listed_symbols
from storage.index_store import save_indexes, load_previous, save_daily_stats
from storage.retention import cleanup


def update_official_prices(collected, results, state, log):
    """After a round: official prices, candles and exchange stats."""
    now = datetime.now(timezone.utc)
    if state.get("countries_at") is None or time.monotonic() - state["countries_at"] > 3600:
        state["countries"] = load_countries()
        state["listed"] = load_listed_symbols()
        state["previous"] = load_previous() if not state.get("previous") else state["previous"]
        state["countries_at"] = time.monotonic()

    indexes, stats, usdt_inr = build_indexes(collected, state["countries"], state["previous"])
    saved = save_indexes(indexes, now, state["listed"])
    state["previous"].update({k: v["price"] for k, v in indexes.items()})
    save_daily_stats(exchange_ids(), results, stats, now.date())
    inr = sum(1 for (_, c) in indexes if c == "INR")
    log(f"  official prices: {saved} ({saved - inr} USD, {inr} INR), USDT-INR {usdt_inr}")


def main():
    exchanges = load_exchanges()

    print("=" * 60, flush=True)
    print("SCANBASE WORKER", flush=True)
    print(f"Exchanges: {', '.join(exchanges)}", flush=True)
    print(f"Collecting every {SECONDS_BETWEEN_RUNS} seconds.", flush=True)
    print("=" * 60, flush=True)

    last_cleanup = None   # None = run cleanup on the first round
    state = {}

    while True:
        started = time.monotonic()
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        print(f"\n[{stamp}] Round starting...", flush=True)

        log = lambda m: print(m, flush=True)
        collected, results = {}, {}
        try:
            results = run_round(exchanges, log=log, collect=collected)
        except Exception as e:
            print(f"Round crashed unexpectedly: {e}", flush=True)

        # Official prices are extra - a failure here never stops collection.
        if collected:
            try:
                update_official_prices(collected, results, state, log)
            except Exception as e:
                print(f"  official prices FAILED - {type(e).__name__}: {e}", flush=True)

        # Once a day: squeeze old hourly history into daily rows.
        # A failure here is logged and retried next time - collection goes on.
        if last_cleanup is None or started - last_cleanup >= CLEANUP_EVERY_HOURS * 3600:
            try:
                cleanup(log=lambda m: print(m, flush=True))
            except Exception as e:
                print(f"  cleanup FAILED - {e}", flush=True)
            last_cleanup = started

        took = time.monotonic() - started
        print(f"[{stamp}] Round done in {took:.1f}s.", flush=True)

        # Wait only the remaining time, so rounds stay roughly 60s apart
        # even when a slow exchange eats part of the minute.
        time.sleep(max(5, SECONDS_BETWEEN_RUNS - took))


if __name__ == "__main__":
    main()
