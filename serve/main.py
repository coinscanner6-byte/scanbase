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

from statistics import median

from fastapi import FastAPI, HTTPException, Header, Query
from fastapi.responses import Response
from sqlalchemy import text

from shared.config import STALE_AFTER_SECONDS, HOURLY_KEEP_DAYS
from storage.db import engine
from ingest.symbols import standardise
from serve.auth import check_key
from serve.logos import logo_url, placeholder_svg
from serve.coin_format import public_description, clean_links
from serve.markets import compute_premium, premium_table, rank_best
from serve.quality_score import score_exchange
from ingest.quality import price_flags, aggregate, group_key

app = FastAPI(
    title="CoinScanner API",
    description=(
        "Live crypto prices collected from multiple exchanges, in one "
        "standard format. Send your key in the `X-API-Key` header."
    ),
    version="0.8.0",
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


QUALITY_SQL = """
    SELECT e.slug,
           SUM(d.rounds_ok), SUM(d.rounds_failed), SUM(d.pairs_sum), SUM(d.wide_sum),
           SUM(d.thin_sum), SUM(d.midpoint_sum), SUM(d.outlier_sum),
           SUM(d.dev_sum), SUM(d.dev_n)
    FROM exchange_daily_stats d
    JOIN exchanges e ON e.id = d.exchange_id
    WHERE d.day >= CURRENT_DATE - 6
    GROUP BY e.slug
"""


def quality_by_exchange(conn):
    out = {}
    for r in conn.execute(text(QUALITY_SQL)).fetchall():
        out[r[0]] = score_exchange({
            "rounds_ok": r[1], "rounds_failed": r[2], "pairs_sum": r[3], "wide_sum": r[4],
            "thin_sum": r[5], "midpoint_sum": r[6], "outlier_sum": r[7],
            "dev_sum": r[8], "dev_n": r[9],
        })
    return out


@app.get("/v1/exchanges")
def list_exchanges(x_api_key: Optional[str] = Header(None)):
    """
    Every exchange we collect from, with our quality rating (last 7 days).
    quality is null until an exchange has enough data (30+ rounds).
    """
    require_key(x_api_key)
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT slug, name, is_active, country FROM exchanges ORDER BY slug")
        ).fetchall()
        quality = quality_by_exchange(conn)
    return [{"slug": r[0], "name": r[1], "is_active": r[2], "country": r[3],
             "quality": quality.get(r[0])} for r in rows]


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
                       s.last_error_at, s.last_error, s.last_warning_at, s.last_warning
                FROM exchanges e
                LEFT JOIN exchange_status s ON s.exchange_id = e.id
                WHERE e.is_active = TRUE
                ORDER BY e.slug
            """)
        ).fetchall()

    result = []
    for slug, name, ok_at, count, err_at, err, warn_at, warn in rows:
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
            # warnings older than a day are hidden
            "warning": warn if warn_at and (now - warn_at).total_seconds() < 86400 else None,
            "warning_at": warn_at.isoformat() if warn_at and (now - warn_at).total_seconds() < 86400 else None,
        })

    return {
        "checked_at": now.isoformat(),
        "stale_after_seconds": STALE_AFTER_SECONDS,
        "healthy_count": sum(1 for r in result if r["healthy"]),
        "exchanges": result,
    }


def usdt_inr_rate(conn):
    r = conn.execute(text(
        "SELECT price FROM index_latest WHERE base = 'USDT' AND currency = 'INR'"
    )).scalar()
    return float(r) if r else None


def index_row_to_dict(r, now):
    age = age_in_seconds(r["updated_at"], now)
    return {
        "price": float(r["price"]),
        "currency": r["currency"],
        "confidence": r["confidence"],
        "sources": r["sources"],
        "exchanges_used": list(r["kept"]),
        "exchanges_excluded": r["excluded"] or {},
        "volume_24h_quote": num(r["volume_quote"]),
        "updated_at": r["updated_at"].isoformat(),
        "age_seconds": age,
        "is_stale": age > STALE_AFTER_SECONDS,
    }


@app.get("/v1/ticker/{symbol}")
def get_ticker(symbol: str, x_api_key: Optional[str] = Header(None)):
    """
    Current price of one pair on every exchange that has it, with
    quality flags, plus the official Scanbase price where one applies.

    Flags: wide_spread, thin_volume, no_volume, estimated_price, outlier.
    Any spelling works: BTCUSDT, BTC-USDT, BTC_USDT.
    """
    require_key(x_api_key)
    wanted = standardise(symbol)

    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT e.slug, e.name, p.symbol, p.price, p.bid, p.ask,
                       p.high_24h, p.low_24h, p.volume_24h, p.collected_at,
                       p.price_source, p.exchange_time, e.country
                FROM prices_latest p
                JOIN exchanges e ON e.id = p.exchange_id
                WHERE p.symbol_std = :wanted
                ORDER BY e.slug
            """),
            {"wanted": wanted},
        ).fetchall()
        usdt_inr = usdt_inr_rate(conn)
        base, quote = (wanted.rsplit("-", 1) + [None])[:2] if "-" in wanted else (wanted, None)
        currency = "INR" if quote == "INR" else "USD" if quote in ("USDT", "USDC") else None
        official = conn.execute(text(
            "SELECT * FROM index_latest WHERE base = :b AND currency = :c"
        ), {"b": base, "c": currency}).mappings().first() if currency else None

    if not rows:
        raise HTTPException(status_code=404, detail=f"No data found for symbol '{symbol}'")

    now = datetime.now(timezone.utc)
    exchanges = []
    for r in rows:
        age = age_in_seconds(r[9], now)
        row = {"symbol_std": wanted, "price": float(r[3]), "bid": num(r[4]), "ask": num(r[5]),
               "volume_24h": num(r[8]), "price_source": r[10]}
        exchanges.append({
            "exchange": r[0],
            "name": r[1],
            "country": r[12],
            "exchange_symbol": r[2],
            "price": row["price"],
            "price_source": r[10],
            "bid": row["bid"],
            "ask": row["ask"],
            "high_24h": num(r[6]),
            "low_24h": num(r[7]),
            "volume_24h": row["volume_24h"],
            "flags": price_flags(row, usdt_inr),
            "collected_at": r[9].isoformat(),
            "exchange_time": r[11].isoformat() if r[11] else None,
            "age_seconds": age,
            "is_stale": age > STALE_AFTER_SECONDS,
        })

    # Mark outliers among the fresh prices, the same way the official price does.
    fresh = [e for e in exchanges if not e["is_stale"]]
    result = aggregate([{"exchange": e["exchange"], "price": e["price"],
                         "volume": e["volume_24h"], "flags": e["flags"]} for e in fresh])
    if result:
        for e in fresh:
            if result["excluded"].get(e["exchange"]) == "outlier":
                e["flags"].append("outlier")

    return {
        "symbol": wanted,
        "exchange_count": len(exchanges),
        "fresh_count": len(fresh),
        "official_price": index_row_to_dict(official, now) if official else None,
        "exchanges": exchanges,
    }


@app.get("/v1/markets")
def list_markets(
    exchange: Optional[str] = None,
    limit: int = Query(1000, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    x_api_key: Optional[str] = Header(None),
):
    """Every pair currently tracked, optionally for one exchange. Paged."""
    require_key(x_api_key)
    where = "WHERE e.slug = :exchange" if exchange else ""
    params = {"exchange": exchange, "limit": limit, "offset": offset}
    with engine.connect() as conn:
        total = conn.execute(text(f"""
            SELECT count(*) FROM prices_latest p JOIN exchanges e ON e.id = p.exchange_id {where}
        """), params).scalar()
        rows = conn.execute(text(f"""
            SELECT p.symbol, p.symbol_std, e.slug
            FROM prices_latest p
            JOIN exchanges e ON e.id = p.exchange_id
            {where}
            ORDER BY p.symbol_std, e.slug
            LIMIT :limit OFFSET :offset
        """), params).fetchall()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
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



# ---------- coins and logos ----------

def num_or_none(value):
    return float(value) if value is not None else None


def day(value):
    return value.isoformat() if value else None


@app.get("/v1/coins")
def list_coins(
    search: Optional[str] = Query(None, description="Match name, symbol or slug"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    x_api_key: Optional[str] = Header(None),
):
    """All coins, best-ranked first. Short info only - use /v1/coins/{coin} for details."""
    require_key(x_api_key)

    where = "WHERE is_active = TRUE"
    params = {"limit": limit, "offset": offset}
    if search:
        where += " AND (name ILIKE :q OR symbol ILIKE :q OR slug ILIKE :q)"
        params["q"] = f"%{search.strip()}%"

    with engine.connect() as conn:
        total = conn.execute(text(f"SELECT count(*) FROM coins {where}"), params).scalar()
        rows = conn.execute(text(f"""
            SELECT slug, symbol, name, rank, categories
            FROM coins {where}
            ORDER BY rank NULLS LAST, name
            LIMIT :limit OFFSET :offset
        """), params).fetchall()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "coins": [
            {"slug": r[0], "symbol": r[1], "name": r[2], "rank": r[3],
             "categories": r[4] or [], "logo_url": logo_url(r[1])}
            for r in rows
        ],
    }


@app.get("/v1/coins/{coin}")
def get_coin(coin: str, x_api_key: Optional[str] = Header(None)):
    """
    Full info for one coin, plus its live USDT price.
    Accepts the slug ("dogecoin") or the symbol ("DOGE"). If several coins
    share a symbol, the best-ranked one is returned.
    """
    require_key(x_api_key)

    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT slug, symbol, name, rank, description, links, categories,
                   contract_addresses, genesis_date, max_supply, total_supply,
                   circulating_supply, ath_usd, ath_date, atl_usd, atl_date,
                   source_updated_at
            FROM coins
            WHERE slug = LOWER(:c) OR UPPER(symbol) = UPPER(:c)
            ORDER BY (slug = LOWER(:c)) DESC, rank NULLS LAST
            LIMIT 1
        """), {"c": coin.strip()}).mappings().first()

        if not row:
            raise HTTPException(status_code=404, detail=f"No coin found for '{coin}'")

        prices = conn.execute(text("""
            SELECT e.slug, p.price, p.collected_at
            FROM prices_latest p
            JOIN exchanges e ON e.id = p.exchange_id
            WHERE p.symbol_std = :pair
              AND p.collected_at >= NOW() - make_interval(secs => :stale)
        """), {"pair": f"{row['symbol']}-USDT", "stale": STALE_AFTER_SECONDS}).fetchall()

    live = [float(p[1]) for p in prices]
    price_usdt = median(live) if live else None
    circulating = num_or_none(row["circulating_supply"])

    return {
        "slug": row["slug"],
        "symbol": row["symbol"],
        "name": row["name"],
        "rank": row["rank"],
        "logo_url": logo_url(row["symbol"]),
        "categories": row["categories"] or [],
        "description": public_description(row["description"]),
        "links": clean_links(row["links"]),
        "contract_addresses": row["contract_addresses"] or {},
        "genesis_date": day(row["genesis_date"]),
        "supply": {
            "circulating": circulating,
            "total": num_or_none(row["total_supply"]),
            "max": num_or_none(row["max_supply"]),
        },
        "all_time": {
            "high_usd": num_or_none(row["ath_usd"]),
            "high_date": day(row["ath_date"]),
            "low_usd": num_or_none(row["atl_usd"]),
            "low_date": day(row["atl_date"]),
        },
        "live": {
            "price_usdt": price_usdt,
            "market_cap_usdt": price_usdt * circulating if price_usdt and circulating else None,
            "exchange_count": len(live),
            "exchanges": sorted(p[0] for p in prices),
        },
        "info_updated_at": row["source_updated_at"].isoformat() if row["source_updated_at"] else None,
    }


@app.get("/v1/logos/{symbol}")
def get_logo(symbol: str):
    """
    A coin's logo image. Open - no key - so it works directly in
    <img src="..."> tags. Unknown symbols get a generated circle.
    """
    wanted = symbol.strip().upper()
    for ext in (".PNG", ".SVG", ".JPG", ".JPEG", ".WEBP"):
        if wanted.endswith(ext):
            wanted = wanted[: -len(ext)]
            break

    if not wanted.isalnum() or len(wanted) > 20:
        raise HTTPException(status_code=400, detail="Invalid symbol")

    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT content_type, data FROM coin_logos WHERE symbol = :s"),
            {"s": wanted},
        ).fetchone()

    if row:
        # Logos rarely change: let browsers and CDNs keep them for a week,
        # so repeat visits don't hit our server at all (saves cost).
        return Response(content=bytes(row[1]), media_type=row[0],
                        headers={"Cache-Control": "public, max-age=604800"})

    return Response(content=placeholder_svg(wanted), media_type="image/svg+xml",
                    headers={"Cache-Control": "public, max-age=86400"})



# ---------- comparisons: India premium and best price ----------

def fresh_rows(conn, where="", params=None):
    """Live prices that are not stale, with each exchange's country."""
    rows = conn.execute(text(f"""
        SELECT e.slug, e.name, e.country, p.symbol_std, p.price, p.bid, p.ask, p.price_source
        FROM prices_latest p
        JOIN exchanges e ON e.id = p.exchange_id
        WHERE e.is_active = TRUE
          AND p.collected_at >= NOW() - make_interval(secs => :stale)
          {where}
    """), {"stale": STALE_AFTER_SECONDS, **(params or {})}).fetchall()
    return [
        {"exchange": r[0], "name": r[1], "country": r[2], "symbol_std": r[3],
         "price": float(r[4]), "bid": num(r[5]), "ask": num(r[6]), "price_source": r[7]}
        for r in rows
    ]


@app.get("/v1/premium")
def list_premium(
    min_india: int = Query(1, ge=1, le=10, description="Minimum Indian exchanges with the coin"),
    min_global: int = Query(1, ge=1, le=10, description="Minimum global exchanges with the coin"),
    sort: str = Query("premium", pattern="^(premium|base)$"),
    x_api_key: Optional[str] = Header(None),
):
    """
    India premium for every coin traded in INR: how much more (or less)
    it costs in India than on global exchanges, converted at the
    USDT-INR rate on Indian exchanges.
    """
    require_key(x_api_key)
    with engine.connect() as conn:
        rows = fresh_rows(conn, "AND (p.symbol_std LIKE '%-INR' OR p.symbol_std LIKE '%-USDT')")

    table = premium_table(rows, min_india, min_global)
    if sort == "premium":
        table.sort(key=lambda p: -abs(p["premium_pct"]))
    usdt_inr = table[0]["usdt_inr"]["rate"] if table else None
    return {"usdt_inr": usdt_inr, "count": len(table), "coins": table}


@app.get("/v1/premium/{base}")
def get_premium(base: str, x_api_key: Optional[str] = Header(None)):
    """India premium for one coin, e.g. BTC."""
    require_key(x_api_key)
    wanted = base.strip().upper()
    with engine.connect() as conn:
        rows = fresh_rows(conn, "AND p.symbol_std IN (:inr, :usdt, 'USDT-INR')",
                          {"inr": f"{wanted}-INR", "usdt": f"{wanted}-USDT"})
    result = compute_premium(wanted, rows)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Can't compare '{wanted}': it needs a fresh INR price on an Indian "
                   f"exchange and a USDT price on a global one.",
        )
    return result


@app.get("/v1/best/{symbol}")
def best_price(
    symbol: str,
    country: Optional[str] = Query(None, description="IN = Indian exchanges only, GLOBAL = global only"),
    x_api_key: Optional[str] = Header(None),
):
    """
    Where to buy a pair cheapest and sell it highest right now.
    Example: BTCINR (Indian exchanges) or BTCUSDT (global).
    """
    require_key(x_api_key)
    wanted = standardise(symbol)
    where = "AND p.symbol_std = :wanted"
    params = {"wanted": wanted}
    if country:
        country = country.strip().upper()
        if country not in ("IN", "GLOBAL"):
            raise HTTPException(status_code=400, detail="country must be IN or GLOBAL")
        where += " AND e.country = :country"
        params["country"] = country
    with engine.connect() as conn:
        rows = fresh_rows(conn, where, params)
    if not rows:
        raise HTTPException(status_code=404, detail=f"No fresh prices for '{symbol}'")
    return {"symbol": wanted, "exchange_count": len(rows), **rank_best(rows)}



# ---------- official prices and candles ----------

def resolve_coin(conn, coin):
    """slug or symbol -> (slug or None, SYMBOL). Best-ranked coin wins a shared symbol."""
    c = coin.strip()
    row = conn.execute(text("""
        SELECT slug, UPPER(symbol) FROM coins
        WHERE slug = LOWER(:c) OR UPPER(symbol) = UPPER(:c)
        ORDER BY (slug = LOWER(:c)) DESC, rank NULLS LAST
        LIMIT 1
    """), {"c": c}).fetchone()
    if row:
        return row[0], row[1]
    return None, c.upper()


@app.get("/v1/prices")
def list_prices(
    currency: str = Query("usd", description="usd or inr"),
    symbols: Optional[str] = Query(None, description="Comma-separated, e.g. BTC,ETH"),
    listed_only: bool = Query(True, description="Only coins with a coin page"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    x_api_key: Optional[str] = Header(None),
):
    """
    Official Scanbase prices. USD comes from global exchanges only,
    INR from Indian exchanges only. Best-ranked coins first.
    """
    require_key(x_api_key)
    cur = currency.strip().upper()
    if cur not in ("USD", "INR"):
        raise HTTPException(status_code=400, detail="currency must be usd or inr")

    where = ["i.currency = :cur"]
    params = {"cur": cur, "limit": limit, "offset": offset}
    if symbols:
        wanted = [x.strip().upper() for x in symbols.split(",") if x.strip()][:200]
        where.append("i.base = ANY(:syms)")
        params["syms"] = wanted
    if listed_only:
        where.append("c.slug IS NOT NULL")
    where_sql = " AND ".join(where)

    base_sql = f"""
        FROM index_latest i
        LEFT JOIN LATERAL (
            SELECT slug, name, rank FROM coins
            WHERE UPPER(symbol) = i.base AND is_active = TRUE
            ORDER BY rank NULLS LAST LIMIT 1
        ) c ON TRUE
        WHERE {where_sql}
    """
    with engine.connect() as conn:
        total = conn.execute(text(f"SELECT count(*) {base_sql}"), params).scalar()
        rows = conn.execute(text(f"""
            SELECT i.*, c.slug, c.name, c.rank {base_sql}
            ORDER BY c.rank NULLS LAST, i.volume_quote DESC NULLS LAST, i.base
            LIMIT :limit OFFSET :offset
        """), params).mappings().all()

    now = datetime.now(timezone.utc)
    return {
        "currency": cur,
        "total": total,
        "limit": limit,
        "offset": offset,
        "prices": [
            {"symbol": r["base"], "coin_id": r["slug"], "name": r["name"], "rank": r["rank"],
             "logo_url": logo_url(r["base"]), **index_row_to_dict(r, now)}
            for r in rows
        ],
    }


@app.get("/v1/prices/{coin}")
def get_price(coin: str, x_api_key: Optional[str] = Header(None)):
    """
    Official USD and INR price for one coin (slug like "bitcoin" or
    symbol like "BTC"), plus the India premium between them.
    """
    require_key(x_api_key)
    with engine.connect() as conn:
        slug, symbol = resolve_coin(conn, coin)
        rows = conn.execute(text(
            "SELECT * FROM index_latest WHERE base = :b"
        ), {"b": symbol}).mappings().all()
        usdt_inr = usdt_inr_rate(conn)

    if not rows:
        raise HTTPException(status_code=404, detail=f"No official price for '{coin}'")

    now = datetime.now(timezone.utc)
    by_cur = {r["currency"]: index_row_to_dict(r, now) for r in rows}
    usd, inr = by_cur.get("USD"), by_cur.get("INR")
    premium = None
    if usd and inr and usdt_inr:
        premium = round((inr["price"] / (usd["price"] * usdt_inr) - 1) * 100, 3)

    return {
        "symbol": symbol,
        "coin_id": slug,
        "logo_url": logo_url(symbol),
        "usd": usd,
        "inr": inr,
        "usdt_inr": usdt_inr,
        "india_premium_pct": premium,
    }


@app.get("/v1/candles/{coin}")
def get_candles(
    coin: str,
    currency: str = Query("usd", description="usd or inr"),
    interval: str = Query("1h", description="1h (last 90 days) or 1d (all history)"),
    days: int = Query(7, ge=1, le=3650),
    x_api_key: Optional[str] = Header(None),
):
    """
    Open/high/low/close candles of the OFFICIAL price, for listed coins.
    Built from one reading per minute, so they are accurate to the minute.
    """
    require_key(x_api_key)
    cur = currency.strip().upper()
    if cur not in ("USD", "INR"):
        raise HTTPException(status_code=400, detail="currency must be usd or inr")
    if interval not in ("1h", "1d"):
        raise HTTPException(status_code=400, detail="interval must be 1h or 1d")
    if interval == "1h" and days > 90:
        raise HTTPException(status_code=400, detail="1h candles go back 90 days - use 1d")

    with engine.connect() as conn:
        slug, symbol = resolve_coin(conn, coin)
        params = {"b": symbol, "c": cur, "days": days}
        if interval == "1h":
            rows = conn.execute(text("""
                SELECT hour AS t, open, high, low, close, samples
                FROM index_candles_1h
                WHERE base = :b AND currency = :c
                  AND hour >= NOW() - make_interval(days => :days)
                ORDER BY hour
            """), params).fetchall()
        else:
            rows = conn.execute(text("""
                SELECT day AS t, open, high, low, close, samples
                FROM index_candles_1d
                WHERE base = :b AND currency = :c
                  AND day >= (NOW() - make_interval(days => :days))::date
                UNION ALL
                SELECT (hour AT TIME ZONE 'UTC')::date,
                       (ARRAY_AGG(open ORDER BY hour ASC))[1], MAX(high), MIN(low),
                       (ARRAY_AGG(close ORDER BY hour DESC))[1], SUM(samples)
                FROM index_candles_1h
                WHERE base = :b AND currency = :c
                  AND hour >= (NOW() - make_interval(days => :days))::date
                GROUP BY (hour AT TIME ZONE 'UTC')::date
                ORDER BY 1
            """), params).fetchall()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No candles for '{coin}' in {cur}. Candles exist for listed coins, "
                   f"starting from when official prices were switched on.",
        )
    return {
        "symbol": symbol,
        "coin_id": slug,
        "currency": cur,
        "interval": interval,
        "count": len(rows),
        "candles": [
            {"t": r[0].isoformat(), "open": float(r[1]), "high": float(r[2]),
             "low": float(r[3]), "close": float(r[4]), "samples": int(r[5])}
            for r in rows
        ],
    }


@app.get("/v1/exchanges/{slug}")
def exchange_detail(slug: str, x_api_key: Optional[str] = Header(None)):
    """One exchange: rating, daily stats for the last 7 days, and current status."""
    require_key(x_api_key)
    with engine.connect() as conn:
        ex = conn.execute(text(
            "SELECT id, slug, name, country, is_active FROM exchanges WHERE slug = LOWER(:s)"
        ), {"s": slug.strip()}).mappings().first()
        if not ex:
            raise HTTPException(status_code=404, detail=f"Unknown exchange '{slug}'")
        days = conn.execute(text("""
            SELECT day, rounds_ok, rounds_failed, pairs_sum, wide_sum, thin_sum,
                   midpoint_sum, outlier_sum, dev_sum, dev_n
            FROM exchange_daily_stats
            WHERE exchange_id = :id AND day >= CURRENT_DATE - 6
            ORDER BY day
        """), {"id": ex["id"]}).fetchall()
        quality = quality_by_exchange(conn).get(ex["slug"])
        pairs = conn.execute(text(
            "SELECT count(*) FROM prices_latest WHERE exchange_id = :id"
        ), {"id": ex["id"]}).scalar()

    return {
        "slug": ex["slug"],
        "name": ex["name"],
        "country": ex["country"],
        "is_active": ex["is_active"],
        "pairs_tracked": pairs,
        "quality": quality,
        "daily": [
            {"day": d[0].isoformat(), "rounds_ok": d[1], "rounds_failed": d[2],
             "avg_pairs": round(d[3] / d[1]) if d[1] else 0,
             "wide_spread_pct": round(d[4] / d[3] * 100, 2) if d[3] else None,
             "thin_volume_pct": round(d[5] / d[3] * 100, 2) if d[3] else None,
             "estimated_price_pct": round(d[6] / d[3] * 100, 2) if d[3] else None,
             "outliers": d[7],
             "avg_deviation_pct": round(d[8] / d[9], 4) if d[9] else None}
            for d in days
        ],
    }
