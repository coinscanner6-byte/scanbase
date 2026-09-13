"""
Scanbase - Stage 1

Runs the whole pipeline ONE TIME:
  1. Fetch prices from Binance
  2. Throw out anything that looks broken
  3. Save the good prices to the database

This does not loop or run in the background yet - that comes once
we've confirmed this basic version actually works end to end.

Run with:
    python3 scripts/run_once.py
"""

import sys
import os
from datetime import datetime, timezone

# Let this script find the other folders (core/, collectors/) when run directly
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from collectors import binance
from core.validate import clean_prices
from core.db import get_exchange_id, save_prices


def main():
    print("=" * 60)
    print("SCANBASE - STAGE 1 - SINGLE RUN")
    print("=" * 60)

    print("\n1. Fetching prices from Binance...")
    raw_prices = binance.fetch()
    print(f"   Got {len(raw_prices)} prices back from Binance.")

    print("\n2. Checking prices for anything broken...")
    good_prices = clean_prices(raw_prices)
    rejected = len(raw_prices) - len(good_prices)
    print(f"   {len(good_prices)} prices passed the check.")
    print(f"   {rejected} were rejected as invalid.")

    print("\n3. Saving to the database...")
    exchange_id = get_exchange_id("binance")
    collected_at = datetime.now(timezone.utc)
    saved_count = save_prices(exchange_id, good_prices, collected_at)
    print(f"   Saved {saved_count} prices.")

    print("\n" + "=" * 60)
    print("DONE. Check your database - the prices_latest table should")
    print("now have rows in it. Run this script again in a minute and")
    print("the SAME rows should update, not duplicate.")
    print("=" * 60)


if __name__ == "__main__":
    main()
