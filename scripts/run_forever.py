"""
Scanbase - runs forever

This is the same pipeline as run_once.py, except instead of running
one time and stopping, it loops forever: collect from all five
exchanges, wait a minute, collect again, wait a minute, repeat.

This is the file that runs on Railway, all day, with nobody watching it.

If one exchange fails on a given cycle, we log it and keep going -
we never want one broken exchange to stop the other four, or to
crash the whole loop.
"""

import sys
import os
import time
from datetime import datetime, timezone

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from collectors import binance, okx, bybit, mexc, gateio
from core.validate import clean_prices
from core.db import get_exchange_id, save_prices

COLLECTORS = {
    "binance": binance,
    "okx": okx,
    "bybit": bybit,
    "mexc": mexc,
    "gateio": gateio,
}

# How long to wait between collection rounds, in seconds.
SECONDS_BETWEEN_RUNS = 60


def run_for_exchange(slug, collector):
    raw_prices = collector.fetch()
    good_prices = clean_prices(raw_prices)
    exchange_id = get_exchange_id(slug)
    collected_at = datetime.now(timezone.utc)
    saved_count = save_prices(exchange_id, good_prices, collected_at)
    return len(raw_prices), len(good_prices), saved_count


def run_one_full_cycle():
    """
    Goes through every exchange once. If one fails, we print why and
    move on - we never want a single bad exchange to take down the
    whole cycle.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"\n[{timestamp}] Starting collection round...")

    for slug, collector in COLLECTORS.items():
        try:
            fetched, passed, saved = run_for_exchange(slug, collector)
            print(f"  {slug}: fetched {fetched}, saved {saved}")
        except Exception as e:
            # Something went wrong with this one exchange - print it and
            # move on. Common causes: the exchange is briefly down, or
            # rate-limiting us. Not a reason to stop everything.
            print(f"  {slug}: FAILED - {e}")

    print(f"[{timestamp}] Round complete.")


def main():
    print("=" * 60)
    print("SCANBASE - RUNNING FOREVER")
    print(f"Collecting from all 5 exchanges every {SECONDS_BETWEEN_RUNS} seconds.")
    print("=" * 60)

    while True:
        run_one_full_cycle()
        time.sleep(SECONDS_BETWEEN_RUNS)


if __name__ == "__main__":
    main()
