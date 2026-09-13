"""
This file knows how to talk to the database. Nothing else in the
project should open a database connection directly - everything
goes through here, so there's only one place to fix if it changes.
"""

import os
from sqlalchemy import create_engine, text
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()  # reads the .env file and makes DATABASE_URL available

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Copy .env.example to .env and fill in "
        "your real database address."
    )

engine = create_engine(DATABASE_URL)


def get_exchange_id(slug):
    """
    Given a short code like 'binance', find its row in the exchanges
    table and return its id number. We look this up once and reuse it,
    rather than writing the exchange name into every price row.
    """
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT id FROM exchanges WHERE slug = :slug"),
            {"slug": slug},
        ).fetchone()
        if result is None:
            raise ValueError(
                f"No exchange found with slug '{slug}'. "
                f"Did you run db/schema.sql against this database?"
            )
        return result[0]


def save_prices(exchange_id, prices, collected_at):
    """
    Save a batch of prices for one exchange, in a single real trip to
    the database rather than one trip per row.

    'prices' is expected to be a list of dicts like:
        [{"symbol": "BTCUSDT", "price": 65000.12}, ...]

    Ordinary batching through SQLAlchemy still sends one row at a time
    behind the scenes when using ON CONFLICT - it just hides the loop
    from us. execute_values (from psycopg2) builds one real statement
    covering every row and sends it once, which is what actually makes
    this fast over a slow connection.
    """
    if not prices:
        return 0

    hour_bucket = collected_at.replace(minute=0, second=0, microsecond=0)

    latest_values = [
        (exchange_id, row["symbol"], row["price"], collected_at)
        for row in prices
    ]
    hourly_values = [
        (exchange_id, row["symbol"], row["price"], hour_bucket)
        for row in prices
    ]

    raw_conn = engine.raw_connection()
    try:
        with raw_conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO prices_latest (exchange_id, symbol, price, collected_at)
                VALUES %s
                ON CONFLICT (exchange_id, symbol)
                DO UPDATE SET price = EXCLUDED.price, collected_at = EXCLUDED.collected_at
                """,
                latest_values,
            )
            execute_values(
                cur,
                """
                INSERT INTO prices_hourly (exchange_id, symbol, price, hour_bucket)
                VALUES %s
                ON CONFLICT (exchange_id, symbol, hour_bucket) DO NOTHING
                """,
                hourly_values,
            )
        raw_conn.commit()
    finally:
        raw_conn.close()

    return len(prices)
