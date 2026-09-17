"""
Creates a new API key for a customer.

Run with:
    python3 -m scripts.create_key "CoinScanner"
    python3 -m scripts.create_key "CoinScanner" 5000   (custom hourly limit)

The key is printed ONCE and never stored in plain form. Copy it
immediately - if it's lost, you cannot recover it, you can only
create a new one.
"""

import sys

from sqlalchemy import text
from storage.db import engine
from serve.auth import generate_key, hash_key
from shared.config import DEFAULT_RATE_LIMIT


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 -m scripts.create_key \"Customer Name\" [hourly_limit]")
        print("Example: python3 -m scripts.create_key \"CoinScanner\"")
        sys.exit(1)

    name = sys.argv[1]
    rate_limit = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_RATE_LIMIT

    raw_key = generate_key()

    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO api_keys (key_hash, name, rate_limit)
                VALUES (:key_hash, :name, :rate_limit)
            """),
            {"key_hash": hash_key(raw_key), "name": name, "rate_limit": rate_limit},
        )

    print("=" * 60)
    print(f"API KEY CREATED FOR: {name}")
    print("=" * 60)
    print()
    print(f"  {raw_key}")
    print()
    print(f"Rate limit: {rate_limit} requests per hour")
    print()
    print("COPY THIS NOW. It is not stored anywhere and cannot be shown")
    print("again. If lost, create a new key instead.")
    print("=" * 60)


if __name__ == "__main__":
    main()
