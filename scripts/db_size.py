"""
Shows how big each table is. Run any time to watch growth.

    python3 -m scripts.db_size
"""

from sqlalchemy import text

from storage.db import engine

TABLES = ["prices_latest", "prices_hourly", "prices_daily",
          "exchange_status", "api_keys", "api_usage"]


def main():
    with engine.connect() as conn:
        total = conn.execute(text("SELECT pg_size_pretty(pg_database_size(current_database()))")).scalar()
        print(f"Whole database: {total}\n")
        print(f"{'table':<18}{'rows':>14}{'size':>12}")
        for t in TABLES:
            exists = conn.execute(text("SELECT to_regclass(:t)"), {"t": t}).scalar()
            if not exists:
                print(f"{t:<18}{'(not created yet)':>26}")
                continue
            rows = conn.execute(text(f"SELECT count(*) FROM {t}")).scalar()
            size = conn.execute(text(f"SELECT pg_size_pretty(pg_total_relation_size('{t}'))")).scalar()
            print(f"{t:<18}{rows:>14,}{size:>12}")

        first = conn.execute(text("SELECT MIN(hour_bucket) FROM prices_hourly")).scalar()
        if first:
            print(f"\nHistory starts: {first}")


if __name__ == "__main__":
    main()
