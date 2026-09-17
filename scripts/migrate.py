"""
Applies every database migration in order.

Every migration file is written to be safe to run more than once, so
running this again on the live database changes nothing that already
exists - it only adds what's missing.

Run with:
    python3 -m scripts.migrate
"""

from pathlib import Path

from storage.db import engine

MIGRATIONS = Path(__file__).resolve().parent.parent / "storage" / "migrations"


def main():
    files = sorted(MIGRATIONS.glob("*.sql"))
    raw = engine.raw_connection()
    try:
        with raw.cursor() as cur:
            for f in files:
                print(f"Applying {f.name}...")
                cur.execute(f.read_text())
        raw.commit()
    finally:
        raw.close()
    print(f"Done. {len(files)} migration files applied.")


if __name__ == "__main__":
    main()
