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
from ingest.pipeline import run_round
from storage.retention import cleanup


def main():
    exchanges = load_exchanges()

    print("=" * 60, flush=True)
    print("SCANBASE WORKER", flush=True)
    print(f"Exchanges: {', '.join(exchanges)}", flush=True)
    print(f"Collecting every {SECONDS_BETWEEN_RUNS} seconds.", flush=True)
    print("=" * 60, flush=True)

    last_cleanup = None   # None = run cleanup on the first round

    while True:
        started = time.monotonic()
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        print(f"\n[{stamp}] Round starting...", flush=True)

        try:
            run_round(exchanges, log=lambda m: print(m, flush=True))
        except Exception as e:
            print(f"Round crashed unexpectedly: {e}", flush=True)

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
