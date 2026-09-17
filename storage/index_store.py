"""Saving official prices, their candles, and per-exchange daily stats."""

import json

from psycopg2.extras import execute_values
from sqlalchemy import text

from storage.db import engine


def save_indexes(indexes, at, candle_symbols):
    """
    indexes: {(base, currency): aggregate result}
    candle_symbols: bases that get hourly candles (listed coins).
    One trip for the latest prices, one for the candles.
    """
    if not indexes:
        return 0
    hour = at.replace(minute=0, second=0, microsecond=0)
    latest = [
        (base, cur, r["price"], r["confidence"], len(r["kept"]), r["kept"],
         json.dumps(r["excluded"]), r["volume_quote"], at)
        for (base, cur), r in indexes.items()
    ]
    candles = [
        (base, cur, hour, r["price"], r["price"], r["price"], r["price"])
        for (base, cur), r in indexes.items() if base in candle_symbols
    ]
    raw = engine.raw_connection()
    try:
        with raw.cursor() as cur:
            execute_values(cur, """
                INSERT INTO index_latest
                    (base, currency, price, confidence, sources, kept, excluded, volume_quote, updated_at)
                VALUES %s
                ON CONFLICT (base, currency) DO UPDATE SET
                    price = EXCLUDED.price, confidence = EXCLUDED.confidence,
                    sources = EXCLUDED.sources, kept = EXCLUDED.kept,
                    excluded = EXCLUDED.excluded, volume_quote = EXCLUDED.volume_quote,
                    updated_at = EXCLUDED.updated_at
            """, latest, template="(%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)", page_size=1000)
            if candles:
                execute_values(cur, """
                    INSERT INTO index_candles_1h (base, currency, hour, open, high, low, close)
                    VALUES %s
                    ON CONFLICT (base, currency, hour) DO UPDATE SET
                        high = GREATEST(index_candles_1h.high, EXCLUDED.high),
                        low = LEAST(index_candles_1h.low, EXCLUDED.low),
                        close = EXCLUDED.close,
                        samples = index_candles_1h.samples + 1
                """, candles, page_size=1000)
        raw.commit()
    finally:
        raw.close()
    return len(latest)


def load_previous():
    """{(base, currency): price} - used to catch wild jumps on thin coins."""
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT base, currency, price FROM index_latest")).fetchall()
    return {(r[0], r[1]): float(r[2]) for r in rows}


def save_daily_stats(exchange_ids, results, stats, day):
    """
    exchange_ids: {slug: id}; results: {slug: "ok" | error}
    stats: from build_indexes - only for exchanges that worked.
    """
    rows = []
    for slug, outcome in results.items():
        ex_id = exchange_ids.get(slug)
        if ex_id is None:
            continue
        ok = outcome == "ok"
        s = stats.get(slug, {}) if ok else {}
        dev = s.get("median_dev_pct")
        rows.append((
            ex_id, day, int(ok), int(not ok),
            s.get("pairs", 0), s.get("wide", 0), s.get("thin", 0),
            s.get("midpoint", 0), s.get("outliers", 0),
            dev or 0.0, 1 if dev is not None else 0,
        ))
    if not rows:
        return
    raw = engine.raw_connection()
    try:
        with raw.cursor() as cur:
            execute_values(cur, """
                INSERT INTO exchange_daily_stats
                    (exchange_id, day, rounds_ok, rounds_failed, pairs_sum, wide_sum,
                     thin_sum, midpoint_sum, outlier_sum, dev_sum, dev_n)
                VALUES %s
                ON CONFLICT (exchange_id, day) DO UPDATE SET
                    rounds_ok = exchange_daily_stats.rounds_ok + EXCLUDED.rounds_ok,
                    rounds_failed = exchange_daily_stats.rounds_failed + EXCLUDED.rounds_failed,
                    pairs_sum = exchange_daily_stats.pairs_sum + EXCLUDED.pairs_sum,
                    wide_sum = exchange_daily_stats.wide_sum + EXCLUDED.wide_sum,
                    thin_sum = exchange_daily_stats.thin_sum + EXCLUDED.thin_sum,
                    midpoint_sum = exchange_daily_stats.midpoint_sum + EXCLUDED.midpoint_sum,
                    outlier_sum = exchange_daily_stats.outlier_sum + EXCLUDED.outlier_sum,
                    dev_sum = exchange_daily_stats.dev_sum + EXCLUDED.dev_sum,
                    dev_n = exchange_daily_stats.dev_n + EXCLUDED.dev_n
            """, rows)
        raw.commit()
    finally:
        raw.close()
