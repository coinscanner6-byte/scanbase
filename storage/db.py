"""
This file knows how to talk to the database. Nothing else in the
project should open a database connection directly - everything
goes through here, so there's only one place to fix if it changes.
"""

from sqlalchemy import create_engine, text
from psycopg2.extras import execute_values

from shared.config import DATABASE_URL

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Copy .env.example to .env and fill in "
        "your real database address."
    )

# pool_pre_ping quietly checks a connection is still alive before using
# it, so a database restart on Railway doesn't cause random errors.
engine = create_engine(DATABASE_URL, pool_pre_ping=True)


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
                f"Did you run storage/migrations/001_schema.sql against this database?"
            )
        return result[0]


def save_prices(exchange_id, prices, collected_at, history_rows=None):
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

    page_size=1000 sends up to 1,000 rows per trip (the default is 100).
    The worker runs in Singapore and the database in California, so
    fewer trips makes each round much faster.

    'history_rows' is the subset worth keeping in permanent hourly
    history (see ingest/history_filter.py). If not given, every row
    goes into history, as before.
    """
    if not prices:
        return 0

    if history_rows is None:
        history_rows = prices

    hour_bucket = collected_at.replace(minute=0, second=0, microsecond=0)

    latest_values = [
        (
            exchange_id, row["symbol"], row.get("symbol_std"), row["price"],
            row.get("bid"), row.get("ask"),
            row.get("high_24h"), row.get("low_24h"), row.get("volume_24h"),
            collected_at, row.get("price_source", "last_trade"),
            row.get("exchange_time"),
        )
        for row in prices
    ]
    hourly_values = [
        (
            exchange_id, row["symbol"], row.get("symbol_std"), row["price"],
            row.get("bid"), row.get("ask"),
            row.get("high_24h"), row.get("low_24h"), row.get("volume_24h"),
            hour_bucket,
        )
        for row in history_rows
    ]

    raw_conn = engine.raw_connection()
    try:
        with raw_conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO prices_latest
                    (exchange_id, symbol, symbol_std, price, bid, ask, high_24h, low_24h, volume_24h, collected_at, price_source, exchange_time)
                VALUES %s
                ON CONFLICT (exchange_id, symbol)
                DO UPDATE SET
                    symbol_std = EXCLUDED.symbol_std,
                    price = EXCLUDED.price,
                    bid = EXCLUDED.bid,
                    ask = EXCLUDED.ask,
                    high_24h = EXCLUDED.high_24h,
                    low_24h = EXCLUDED.low_24h,
                    volume_24h = EXCLUDED.volume_24h,
                    collected_at = EXCLUDED.collected_at,
                    price_source = EXCLUDED.price_source,
                    exchange_time = EXCLUDED.exchange_time
                """,
                latest_values,
                page_size=1000,
            )
            if hourly_values:
                execute_values(
                    cur,
                    """
                    INSERT INTO prices_hourly
                        (exchange_id, symbol, symbol_std, price, bid, ask, high_24h, low_24h, volume_24h, hour_bucket)
                    VALUES %s
                    ON CONFLICT (exchange_id, symbol, hour_bucket) DO NOTHING
                    """,
                    hourly_values,
                    page_size=1000,
                )
        raw_conn.commit()
    finally:
        raw_conn.close()

    return len(prices)


def record_success(exchange_id, saved_count, at):
    """
    Notes that this exchange worked this round, and clears any old
    error - once an exchange recovers, /v1/status stops showing it.
    """
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO exchange_status (exchange_id, last_success_at, last_saved_count, updated_at)
                VALUES (:id, :at, :count, :at)
                ON CONFLICT (exchange_id) DO UPDATE SET
                    last_success_at = EXCLUDED.last_success_at,
                    last_saved_count = EXCLUDED.last_saved_count,
                    last_error_at = NULL,
                    last_error = NULL,
                    updated_at = EXCLUDED.updated_at
            """),
            {"id": exchange_id, "count": saved_count, "at": at},
        )


def record_failure(exchange_id, error_message, at):
    """Notes that this exchange failed this round, and why."""
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO exchange_status (exchange_id, last_error_at, last_error, updated_at)
                VALUES (:id, :at, :error, :at)
                ON CONFLICT (exchange_id) DO UPDATE SET
                    last_error_at = EXCLUDED.last_error_at,
                    last_error = EXCLUDED.last_error,
                    updated_at = EXCLUDED.updated_at
            """),
            {"id": exchange_id, "error": error_message[:500], "at": at},
        )


def record_warning(exchange_id, message, at):
    """A non-fatal problem, e.g. far fewer pairs than usual (API may have changed)."""
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO exchange_status (exchange_id, last_warning_at, last_warning, updated_at)
                VALUES (:id, :at, :msg, :at)
                ON CONFLICT (exchange_id) DO UPDATE SET
                    last_warning_at = EXCLUDED.last_warning_at,
                    last_warning = EXCLUDED.last_warning,
                    updated_at = EXCLUDED.updated_at
            """),
            {"id": exchange_id, "msg": message[:500], "at": at},
        )


def load_countries():
    """{exchange slug: country} for every exchange."""
    with engine.connect() as conn:
        return dict(conn.execute(text("SELECT slug, COALESCE(country, 'GLOBAL') FROM exchanges")).fetchall())


def load_listed_symbols():
    """Symbols of listed coins - the ones that get official-price candles."""
    with engine.connect() as conn:
        return set(conn.execute(text(
            "SELECT DISTINCT UPPER(symbol) FROM coins WHERE is_active = TRUE"
        )).scalars().all())
