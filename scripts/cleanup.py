"""
History clean-up by hand. The worker also runs the normal clean-up daily.

    python3 -m scripts.cleanup --preview   READ-ONLY: what --purge would delete
    python3 -m scripts.cleanup             normal clean-up (old hourly -> daily)
    python3 -m scripts.cleanup --purge     ALSO delete junk history saved before
                                           the filter existed (asks to confirm)
"""

import sys

from shared.config import HISTORY_QUOTES, MIN_HISTORY_VOLUME_USD
from storage.retention import cleanup, purge_unwanted_history, preview_purge


def show_preview():
    p = preview_purge()
    pct = (p["unwanted"] / p["total"] * 100) if p["total"] else 0
    print(f"Rule: keep {', '.join(HISTORY_QUOTES)} pairs; USDT/USDC need "
          f"${MIN_HISTORY_VOLUME_USD:,}+ traded in 24h; INR always kept.\n")
    print(f"Hourly rows now:        {p['total']:>12,}")
    print(f"Would be deleted:       {p['unwanted']:>12,}  ({pct:.0f}%)")
    print(f"Would be kept:          {p['kept']:>12,}")
    print(f"Pairs in history now:   {p['pairs_before']:>12,}")
    print(f"Pairs after purge:      {p['pairs_after']:>12,}")


def main():
    if "--preview" in sys.argv:
        show_preview()
        print("\nNothing was changed.")
        return

    if "--purge" in sys.argv:
        show_preview()
        print("\nLive prices are not touched. This cannot be undone.")
        if input("Type YES to delete: ").strip() != "YES":
            print("Cancelled.")
            return
        purge_unwanted_history()

    cleanup()
    print("Done. Run  python3 -m scripts.db_size  to see the new sizes.")
    if "--purge" in sys.argv:
        print("Note: Postgres frees the disk space gradually; the size may not drop immediately.")


if __name__ == "__main__":
    main()
