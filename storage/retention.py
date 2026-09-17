"""
Keeps the history table from growing forever.

Once a day:
  1. Hourly rows older than HOURLY_KEEP_DAYS are summarised into
     prices_daily (one row per pair per day).
  2. Only after that succeeds, those hourly rows are deleted - in
     small batches, so the database never locks up.

Summarising uses ON CONFLICT DO NOTHING, so a crash halfway through
is harmless: the next run simply continues.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from shared.config import HOURLY_KEEP_DAYS, CANDLE_HOURLY_KEEP_DAYS
from storage.db import engine

DELETE_BATCH = 50_000


def cleanup(log=print):
    cutoff = (datetime.now(timezone.utc) - timedelta(days=HOURLY_KEEP_DAYS)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    with engine.begin() as conn:
        summarised = conn.execute(
            text("""
                INSERT INTO prices_daily
                    (exchange_id, symbol, symbol_std, day, open, high, low, close,
                     avg_price, volume_24h, samples)
                SELECT
                    exchange_id,
                    symbol,
                    MAX(symbol_std),
                    (hour_bucket AT TIME ZONE 'UTC')::date AS day,
                    (ARRAY_AGG(price ORDER BY hour_bucket ASC))[1],
                    MAX(price),
                    MIN(price),
                    (ARRAY_AGG(price ORDER BY hour_bucket DESC))[1],
                    AVG(price),
                    (ARRAY_AGG(volume_24h ORDER BY hour_bucket DESC))[1],
                    COUNT(*)
                FROM prices_hourly
                WHERE hour_bucket < :cutoff
                GROUP BY exchange_id, symbol, (hour_bucket AT TIME ZONE 'UTC')::date
                ON CONFLICT (exchange_id, symbol, day) DO NOTHING
            """),
            {"cutoff": cutoff},
        ).rowcount

    deleted = 0
    while True:
        with engine.begin() as conn:
            n = conn.execute(
                text("""
                    DELETE FROM prices_hourly
                    WHERE id IN (
                        SELECT id FROM prices_hourly
                        WHERE hour_bucket < :cutoff
                        LIMIT :batch
                    )
                """),
                {"cutoff": cutoff, "batch": DELETE_BATCH},
            ).rowcount
        deleted += n
        if n < DELETE_BATCH:
            break

    log(f"  cleanup: cutoff {cutoff.date()}, {summarised} daily rows added, "
        f"{deleted} hourly rows removed")
    cleanup_candles_and_stats(log)
    return summarised, deleted


def cleanup_candles_and_stats(log=print):
    """Official-price candles: hourly -> daily after 90 days. Stats kept 90 days."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=CANDLE_HOURLY_KEEP_DAYS)).replace(
        hour=0, minute=0, second=0, microsecond=0)
    with engine.begin() as conn:
        rolled = conn.execute(text("""
            INSERT INTO index_candles_1d (base, currency, day, open, high, low, close, samples)
            SELECT base, currency, (hour AT TIME ZONE 'UTC')::date,
                   (ARRAY_AGG(open ORDER BY hour ASC))[1], MAX(high), MIN(low),
                   (ARRAY_AGG(close ORDER BY hour DESC))[1], SUM(samples)
            FROM index_candles_1h
            WHERE hour < :cutoff
            GROUP BY base, currency, (hour AT TIME ZONE 'UTC')::date
            ON CONFLICT (base, currency, day) DO NOTHING
        """), {"cutoff": cutoff}).rowcount
        removed = conn.execute(text("DELETE FROM index_candles_1h WHERE hour < :cutoff"),
                               {"cutoff": cutoff}).rowcount
        stats = conn.execute(text("DELETE FROM exchange_daily_stats WHERE day < :d"),
                             {"d": cutoff.date()}).rowcount
    log(f"  candles: {rolled} daily added, {removed} hourly removed; {stats} old stats removed")


def _unwanted_where():
    """
    The rule for history saved before the filter existed - the same
    rule as ingest/history_filter.py, written in SQL:
      - pair not priced in HISTORY_QUOTES          -> unwanted
      - priced in USDT/USDC but dollar volume below
        MIN_HISTORY_VOLUME_USD                     -> unwanted
      - INR pairs, and rows with no volume         -> kept
    """
    from shared.config import (HISTORY_QUOTES, HISTORY_ALWAYS_KEEP_QUOTES,
                               MIN_HISTORY_VOLUME_USD)

    params = {
        "keep_patterns": [f"%-{q}" for q in HISTORY_QUOTES],
        "always_patterns": [f"%-{q}" for q in HISTORY_ALWAYS_KEEP_QUOTES] or ["__none__"],
        "min_usd": MIN_HISTORY_VOLUME_USD,
    }
    where = """
        symbol_std IS NULL
        OR NOT (symbol_std LIKE ANY(:keep_patterns))
        OR (
            NOT (symbol_std LIKE ANY(:always_patterns))
            AND volume_24h IS NOT NULL
            AND price * volume_24h < :min_usd
        )
    """
    return where, params


def preview_purge():
    """Read-only: how many hourly rows the purge WOULD delete."""
    where, params = _unwanted_where()
    with engine.connect() as conn:
        total = conn.execute(text("SELECT count(*) FROM prices_hourly")).scalar()
        unwanted = conn.execute(
            text(f"SELECT count(*) FROM prices_hourly WHERE {where}"), params
        ).scalar()
        pairs_before = conn.execute(
            text("SELECT count(DISTINCT (exchange_id, symbol)) FROM prices_hourly")
        ).scalar()
        pairs_after = conn.execute(
            text(f"SELECT count(DISTINCT (exchange_id, symbol)) FROM prices_hourly WHERE NOT ({where})"),
            params,
        ).scalar()
    return {"total": total, "unwanted": unwanted, "kept": total - unwanted,
            "pairs_before": pairs_before, "pairs_after": pairs_after}


def purge_unwanted_history(log=print):
    """
    ONE-TIME tidy-up of history saved before the filter existed.
    Deletes in batches so the live worker keeps running meanwhile.
    """
    where, params = _unwanted_where()
    params = dict(params, batch=DELETE_BATCH)
    deleted = 0
    while True:
        with engine.begin() as conn:
            n = conn.execute(
                text(f"""
                    DELETE FROM prices_hourly
                    WHERE id IN (
                        SELECT id FROM prices_hourly
                        WHERE {where}
                        LIMIT :batch
                    )
                """),
                params,
            ).rowcount
        deleted += n
        log(f"  removed {deleted:,} rows so far...")
        if n < DELETE_BATCH:
            break
    return deleted
