"""
Scanbase API - the ISSUE side.

Nothing here collects data. It only reads what the worker has saved.
Collecting and serving run as two separate Railway services, so a
problem in one never breaks the other.

Run locally with:
    uvicorn serve.main:app --reload
Interactive docs (auto-generated):
    http://localhost:8000/docs
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Header, Query
from sqlalchemy import text

from shared.config import STALE_AFTER_SECONDS, HOURLY_KEEP_DAYS
from storage.db import engine
from ingest.symbols import standardise
from serve.auth import check_key

app = FastAPI(
    title="CoinScanner API",
    description=(
        "Live crypto prices collected from multiple exchanges, in one "
        "standard format. Send your key in the `X-API-Key` header."
    ),
    version="0.3.0",
)


# ---------- helpers ----------

def require_key(api_key):
    """
    401 = we don't know who you are (wrong or missing key).
    429 = we know you, but slow down (over the hourly limit).
    """
    result = check_key(api_key)
    if result["ok"]:
        return result
    if result["reason"] == "rate_limited":
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again next hour.")
    raise HTTPException(
        status_code=401,
        detail="Missing or invalid API key. Send it in the 'X-API-Key' header.",
    )


def num(value):
    return float(value) if value is not None else None


def age_in_seconds(moment, now):
    return int((now - moment).total_seconds()) if moment else None


# ---------- endpoints ----------

@app.get("/v1/health")
def health():
    """
    Open, no key needed - Railway and monitoring tools use it.
    Also confirms the database is reachable.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "ok"}
    except Exception:
        raise HTTPException(status_code=503, detail={"status": "degraded", "database": "unreachable"})


@app.get("/v1/exchanges")
def list_exchanges(x_api_key: Optional[str] = Header(None)):
    """Every exchange we collect from."""
    require_key(x_api_key)
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT slug, name, is_active FROM exchanges ORDER BY slug")
        ).fetchall()
    return [{"slug": r[0], "name": r[1], "is_active": r[2]} for r in rows]


@app.get("/v1/status")
def exchange_status(x_api_key: Optional[str] = Header(None)):
    """
    Is each exchange working right now? Shows the last good round,
    the last failure and its reason, and whether data is stale.
    """
    require_key(x_api_key)
    now = datetime.now(timezone.utc)
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT e.slug, e.name, s.last_success_at, s.last_saved_count,
                       s.last_error_at, s.last_error
                FROM exchanges e
                LEFT JOIN exchange_status s ON s.exchange_id = e.id
                WHERE e.is_active = TRUE
                ORDER BY e.slug
            """)
        ).fetchall()

    result = []
    for slug, name, ok_at, count, err_at, err in rows:
        age = age_in_seconds(ok_at, now)
        healthy = age is not None and age <= STALE_AFTER_SECONDS
        result.append({
            "exchange": slug,
            "name": name,
            "healthy": healthy,
            "last_success_at": ok_at.isoformat() if ok_at else None,
            "seconds_since_success": age,
            "last_saved_count": count,
            "last_error_at": err_at.isoformat() if err_at else None,
            "last_error": err,
        })

    return {
        "checked_at": now.isoformat(),
        "stale_after_seconds": STALE_AFTER_SECONDS,
        "healthy_count": sum(1 for r in result if r["healthy"]),
        "exchanges": result,
    }


@app.get("/v1/ticker/{symbol}")
def get_ticker(symbol: str, x_api_key: Optional[str] = Header(None)):
    """
    Current price of one pair from every exchange that has it.
    Any spelling works: BTCUSDT, BTC-USDT, BTC_USDT.
    Each price says how old it is and whether it's stale.
    """
    require_key(x_api_key)
    wanted = standardise(symbol)

    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT e.slug, e.name, p.symbol, p.price, p.bid, p.ask,
                       p.high_24h, p.low_24h, p.volume_24h, p.collected_at
                FROM prices_latest p
                JOIN exchanges e ON e.id = p.exchange_id
                WHERE p.symbol_std = :wanted
                ORDER BY e.slug
            """),
            {"wanted": wanted},
        ).fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail=f"No data found for symbol '{symbol}'")

    now = datetime.now(timezone.utc)
    exchanges = []
    for r in rows:
        age = age_in_seconds(r[9], now)
        exchanges.append({
            "exchange": r[0],
            "name": r[1],
            "exchange_symbol": r[2],   # what this exchange itself calls it
            "price": num(r[3]),
            "bid": num(r[4]),
            "ask": num(r[5]),
            "high_24h": num(r[6]),
            "low_24h": num(r[7]),
            "volume_24h": num(r[8]),
            "collected_at": r[9].isoformat(),
            "age_seconds": age,
            "is_stale": age > STALE_AFTER_SECONDS,
        })

    return {
        "symbol": wanted,
        "exchange_count": len(exchanges),
        "fresh_count": sum(1 for e in exchanges if not e["is_stale"]),
        "exchanges": exchanges,
    }


@app.get("/v1/markets")
def list_markets(exchange: Optional[str] = None, x_api_key: Optional[str] = Header(None)):
    """Every pair currently tracked, optionally for one exchange."""
    require_key(x_api_key)

    sql = """
        SELECT p.symbol, p.symbol_std, e.slug
        FROM prices_latest p
        JOIN exchanges e ON e.id = p.exchange_id
        {where}
        ORDER BY p.symbol_std, e.slug
    """
    with engine.connect() as conn:
        if exchange:
            rows = conn.execute(text(sql.format(where="WHERE e.slug = :exchange")),
                                {"exchange": exchange}).fetchall()
        else:
            rows = conn.execute(text(sql.format(where=""))).fetchall()

    return {
        "count": len(rows),
        "markets": [{"symbol": r[1], "exchange_symbol": r[0], "exchange": r[2]} for r in rows],
    }


@app.get("/v1/history/{symbol}")
def get_history(
    symbol: str,
    interval: str = Query("hour", pattern="^(hour|day)$",
                          description="hour = one price per hour (last 90 days); "
                                      "day = open/high/low/close per day (all history)"),
    days: int = Query(7, ge=1, le=3650, description="How far back to go"),
    exchange: Optional[str] = Query(None, description="One exchange only, e.g. binance"),
    x_api_key: Optional[str] = Header(None),
):
    """
    Past prices for one pair - what CoinScanner needs for charts.

    Only pairs kept in history are available (USDT/USDC with real
    trading, and all INR pairs). Any spelling works: BTCUSDT, BTC-USDT.
    """
    require_key(x_api_key)
    wanted = standardise(symbol)

    if interval == "hour" and days > HOURLY_KEEP_DAYS:
        raise HTTPException(
            status_code=400,
            detail=f"Hourly history only goes back {HOURLY_KEEP_DAYS} days. "
                   f"Use interval=day for longer periods.",
        )

    params = {"wanted": wanted, "days": days, "exchange": exchange}
    exchange_filter = "AND e.slug = :exchange" if exchange else ""

    if interval == "hour":
        sql = f"""
            SELECT e.slug, h.hour_bucket AS t, h.price, h.volume_24h
            FROM prices_hourly h
            JOIN exchanges e ON e.id = h.exchange_id
            WHERE h.symbol_std = :wanted
              AND h.hour_bucket >= NOW() - make_interval(days => :days)
              {exchange_filter}
            ORDER BY e.slug, t
        """
    else:
        # Older days live in prices_daily; recent days are still hourly
        # rows, so we summarise those on the fly. The clean-up job
        # deletes hourly rows once summarised, so a day never appears twice.
        sql = f"""
            WITH combined AS (
                SELECT d.exchange_id, d.day, d.open, d.high, d.low, d.close
                FROM prices_daily d
                WHERE d.symbol_std = :wanted
                  AND d.day >= (NOW() - make_interval(days => :days))::date
                UNION ALL
                SELECT h.exchange_id,
                       (h.hour_bucket AT TIME ZONE 'UTC')::date,
                       (ARRAY_AGG(h.price ORDER BY h.hour_bucket ASC))[1],
                       MAX(h.price),
                       MIN(h.price),
                       (ARRAY_AGG(h.price ORDER BY h.hour_bucket DESC))[1]
                FROM prices_hourly h
                WHERE h.symbol_std = :wanted
                  AND h.hour_bucket >= (NOW() - make_interval(days => :days))::date
                GROUP BY h.exchange_id, h.symbol, (h.hour_bucket AT TIME ZONE 'UTC')::date
            )
            SELECT e.slug, c.day AS t, c.open, c.high, c.low, c.close
            FROM combined c
            JOIN exchanges e ON e.id = c.exchange_id
            WHERE TRUE {exchange_filter}
            ORDER BY e.slug, t
        """

    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).fetchall()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No history for '{symbol}'. It may be a pair we don't keep "
                   f"in history, or collection started too recently.",
        )

    by_exchange = {}
    for r in rows:
        if interval == "hour":
            point = {"t": r[1].isoformat(), "price": num(r[2]), "volume_24h": num(r[3])}
        else:
            point = {"t": r[1].isoformat(), "open": num(r[2]), "high": num(r[3]),
                     "low": num(r[4]), "close": num(r[5])}
        by_exchange.setdefault(r[0], []).append(point)

    return {
        "symbol": wanted,
        "interval": interval,
        "days": days,
        "exchanges": [
            {"exchange": slug, "points": len(pts), "data": pts}
            for slug, pts in by_exchange.items()
        ],
    }
