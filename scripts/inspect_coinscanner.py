"""
READ-ONLY look at CoinScanner's coin table, so the import into
Scanbase can be built on the real column names instead of guesses.

It opens the connection in read-only mode - it cannot change anything.
It never prints the database password.

    python3 -m scripts.inspect_coinscanner ~/Downloads/v5-live/.env
"""

import sys
from pathlib import Path
from urllib.parse import urlparse

from dotenv import dotenv_values
from sqlalchemy import create_engine, text


def short(value, limit=80):
    s = str(value)
    return s if len(s) <= limit else s[:limit] + f"... ({len(s)} chars)"


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 -m scripts.inspect_coinscanner <path to CoinScanner .env>")
        sys.exit(1)

    env_path = Path(sys.argv[1]).expanduser()
    url = dotenv_values(env_path).get("DATABASE_URL")
    if not url:
        print(f"No DATABASE_URL in {env_path}")
        sys.exit(1)

    host = urlparse(url).hostname
    print(f"CoinScanner database host: {host}")
    if host and host.endswith(".railway.internal"):
        print("\nThis is Railway's INTERNAL address - it only works inside Railway.")
        print("Get the PUBLIC one: Railway -> coinscanner project -> Postgres ->")
        print("Variables -> copy DATABASE_PUBLIC_URL, then run (paste inside the quotes):")
        print("  echo 'DATABASE_URL=PASTE_HERE' > /tmp/cs.env")
        print("  python3 -m scripts.inspect_coinscanner /tmp/cs.env")
        sys.exit(1)

    engine = create_engine(url.replace("postgres://", "postgresql://", 1))
    with engine.connect() as conn:
        conn.execute(text("SET TRANSACTION READ ONLY"))

        tables = conn.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' ORDER BY table_name
        """)).scalars().all()
        print(f"\nTables: {', '.join(tables)}")

        coin_tables = [t for t in tables if "coin" in t.lower()]
        for table in coin_tables:
            count = conn.execute(text(f'SELECT count(*) FROM "{table}"')).scalar()
            print(f"\n=== {table}  ({count:,} rows) ===")
            cols = conn.execute(text("""
                SELECT column_name, data_type FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = :t
                ORDER BY ordinal_position
            """), {"t": table}).fetchall()
            for name, dtype in cols:
                print(f"  {name:<28} {dtype}")

            sample = conn.execute(text(f'SELECT * FROM "{table}" LIMIT 1')).mappings().first()
            if sample:
                print("  --- sample row ---")
                for k, v in sample.items():
                    print(f"  {k:<28} {short(v)}")


if __name__ == "__main__":
    main()
