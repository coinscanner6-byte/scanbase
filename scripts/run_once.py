"""
Scanbase - Stage 2

Runs the whole pipeline for ONE OR MORE exchanges:
  1. Fetch prices
  2. Throw out anything that looks broken
  3. Save the good prices to the database

Run with:
    python3 scripts/run_once.py
"""

import sys
import os
from datetime import datetime, timezone

# Let this script find the other folders (core/, collectors/) when run directly
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from collectors import binance, okx, bybit
from core.validate import clean_prices
from core.db import get_exchange_id, save_prices

# Add a new exchange here once its collector file exists, and it will
# automatically be included in every run - nothing else needs to change.
COLLECTORS = {
    "binance": binance,
    "okx": okx,
    "bybit": bybit,
}


def run_for_exchange(slug, collector):
    print(f"\n--- {slug.upper()} ---")

    print("1. Fetching prices...")
    raw_prices = collector.fetch()
    print(f"   Got {len(raw_prices)} prices back.")

    print("2. Checking prices for anything broken...")
    good_prices = clean_prices(raw_prices)
    rejected = len(raw_prices) - len(good_prices)
    print(f"   {len(good_prices)} passed. {rejected} rejected.")

    print("3. Saving to the database...")
    exchange_id = get_exchange_id(slug)
    collected_at = datetime.now(timezone.utc)
    saved_count = save_prices(exchange_id, good_prices, collected_at)
    print(f"   Saved {saved_count} prices.")


def main():
    print("=" * 60)
    print("SCANBASE - STAGE 2 - MULTI EXCHANGE RUN")
    print("=" * 60)

    for slug, collector in COLLECTORS.items():
        try:
            run_for_exchange(slug, collector)
        except Exception as e:
            # If one exchange fails, we print the problem and move on to
            # the next one rather than stopping the whole run. A problem
            # with OKX should never stop us from still collecting Binance.
            print(f"   FAILED: {e}")

    print("\n" + "=" * 60)
    print("DONE.")
    print("=" * 60)


if __name__ == "__main__":
    main()
