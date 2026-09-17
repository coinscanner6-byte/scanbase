"""
Runs ONE collection round and stops. For testing on your Mac.

Run all exchanges:
    python3 -m scripts.run_once
Run just one or a few:
    python3 -m scripts.run_once binance okx
"""

import sys

from ingest.registry import load_exchanges
from ingest.pipeline import run_round


def main():
    exchanges = load_exchanges()
    wanted = sys.argv[1:]

    if wanted:
        unknown = [w for w in wanted if w not in exchanges]
        if unknown:
            print(f"Unknown exchange(s): {', '.join(unknown)}")
            print(f"Available: {', '.join(exchanges)}")
            sys.exit(1)
        exchanges = {slug: exchanges[slug] for slug in wanted}

    print(f"Running once for: {', '.join(exchanges)}")
    collected = {}
    results = run_round(exchanges, collect=collected)
    if collected and not wanted:
        from ingest.worker import update_official_prices
        update_official_prices(collected, results, {}, print)
    failed = [s for s, r in results.items() if r != "ok"]
    print(f"\nDone. {len(results) - len(failed)} ok, {len(failed)} failed.")


if __name__ == "__main__":
    main()
