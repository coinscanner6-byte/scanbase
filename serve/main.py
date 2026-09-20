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
from fastapi.responses import Response, HTMLResponse
from sqlalchemy import text

from shared.config import (STALE_AFTER_SECONDS, HOURLY_KEEP_DAYS, PUBLIC_BASE_URL,
                           TDS_PCT, GST_ON_FEE_PCT, FEE_STALE_DAYS)
from storage.db import engine
from ingest.symbols import standardise
from serve.auth import check_key
from serve.logos import logo_url, placeholder_svg
from serve.coin_format import public_description, clean_links
from serve.markets import compute_premium, premium_table, rank_best
from serve.quality_score import score_exchange
from storage.fx import load_rate
from serve.pages import landing_html, docs_html
from serve.cache import cached
from shared.calc import trade_cost, is_leveraged_token, USEFUL_QUOTES
from ingest.quality import price_flags, aggregate, group_key

TAGS = [
    {"name": "Prices", "description": "Official prices, market cap, change and candles."},
    {"name": "India", "description": "What a coin really costs an Indian buyer."},
    {"name": "Exchanges", "description": "Who we read, how well they behave, and their raw prices."},
    {"name": "Coins", "description": "Names, details and logos."},
    {"name": "Service", "description": "Health and demo data."},
]

app = FastAPI(
    title="CoinScanner API",
    description=(
        "Live crypto prices from ten exchanges, turned into one official price per "
        "coin in dollars and in rupees. Every price carries its age, so old data "
        "can never look live."
    ),
    version="0.9.0",
    openapi_tags=TAGS,
    docs_url=None,          # replaced by our own page, see /docs below
    redoc_url=None,
)


def _openapi():
    """Add the API-key box to the docs page without touching every endpoint."""
    if app.openapi_schema:
        return app.openapi_schema
    from fastapi.openapi.utils import get_openapi
    schema = get_openapi(title=app.title, version=app.version,
                         description=app.description, tags=TAGS, routes=app.routes)
    schema["components"]["securitySchemes"] = {
        "ApiKeyHeader": {"type": "apiKey", "in": "header", "name": "X-API-Key"}
    }
    for path, methods in schema["paths"].items():
        if path.startswith("/v1/health") or path.startswith("/v1/demo") or path == "/":
            continue
        for operation in methods.values():
            operation["security"] = [{"ApiKeyHeader": []}]
    app.openapi_schema = schema
    return schema


app.openapi = _openapi


@app.get("/", include_in_schema=False)
def front_page():
    return HTMLResponse(landing_html(PUBLIC_BASE_URL))


@app.get("/docs", include_in_schema=False)
def interactive_docs():
    return HTMLResponse(docs_html(app.openapi_url))


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

@app.get("/v1/health", tags=["Service"])
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


@app.get("/v1/exchanges", tags=["Exchanges"])
def list_exchanges(x_api_key: Optional[str] = Header(None, include_in_schema=False)):
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


@app.get("/v1/status", tags=["Exchanges"])
def exchange_status(x_api_key: Optional[str] = Header(None, include_in_schema=False)):
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


def pct(value):
    return round(float(value), 4) if value is not None else None


def index_row_to_dict(r, now):
    age = age_in_seconds(r["updated_at"], now)
    return {
        "price": float(r["price"]),
        "market_cap": num(r.get("market_cap")),
        "change_1h_pct": pct(r.get("change_1h")),
        "change_24h_pct": pct(r.get("change_24h")),
        "change_7d_pct": pct(r.get("change_7d")),
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


@app.get("/v1/ticker/{symbol}", tags=["Exchanges"])
def get_ticker(symbol: str, x_api_key: Optional[str] = Header(None, include_in_schema=False)):
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


@app.get("/v1/markets", tags=["Exchanges"])
def list_markets(
    exchange: Optional[str] = None,
    limit: int = Query(1000, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    x_api_key: Optional[str] = Header(None, include_in_schema=False),
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


@app.get("/v1/history/{symbol}", tags=["Exchanges"])
def get_history(
    symbol: str,
    interval: str = Query("hour", pattern="^(hour|day)$",
                          description="hour = one price per hour (last 90 days); "
                                      "day = open/high/low/close per day (all history)"),
    days: int = Query(7, ge=1, le=3650, description="How far back to go"),
    exchange: Optional[str] = Query(None, description="One exchange only, e.g. binance"),
    x_api_key: Optional[str] = Header(None, include_in_schema=False),
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


@app.get("/v1/coins", tags=["Coins"])
def list_coins(
    search: Optional[str] = Query(None, description="Match name, symbol or slug"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    x_api_key: Optional[str] = Header(None, include_in_schema=False),
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


@app.get("/v1/coins/{coin}", tags=["Coins"])
def get_coin(coin: str, x_api_key: Optional[str] = Header(None, include_in_schema=False)):
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


@app.get("/v1/logos/{symbol}", tags=["Coins"])
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


@app.get("/v1/premium", tags=["India"])
def list_premium(
    min_india: int = Query(1, ge=1, le=10, description="Minimum Indian exchanges with the coin"),
    min_global: int = Query(1, ge=1, le=10, description="Minimum global exchanges with the coin"),
    sort: str = Query("premium", pattern="^(premium|base)$"),
    x_api_key: Optional[str] = Header(None, include_in_schema=False),
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


@app.get("/v1/premium/{base}", tags=["India"])
def get_premium(base: str, x_api_key: Optional[str] = Header(None, include_in_schema=False)):
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


@app.get("/v1/best/{symbol}", tags=["India"])
def best_price(
    symbol: str,
    country: Optional[str] = Query(None, description="IN = Indian exchanges only, GLOBAL = global only"),
    x_api_key: Optional[str] = Header(None, include_in_schema=False),
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


SORTS = {
    "market_cap": "i.market_cap",
    "volume": "i.volume_quote",
    "price": "i.price",
    "change_1h": "i.change_1h",
    "change_24h": "i.change_24h",
    "change_7d": "i.change_7d",
    "rank": "c.rank",
}


@app.get("/v1/prices", tags=["Prices"])
def list_prices(
    currency: str = Query("usd", description="usd or inr"),
    symbols: Optional[str] = Query(None, description="Comma-separated, e.g. BTC,ETH"),
    listed_only: bool = Query(True, description="Only coins with a coin page"),
    sort: str = Query("market_cap", description="market_cap, volume, price, change_1h, change_24h, change_7d, rank"),
    order: str = Query("desc", description="desc or asc"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    x_api_key: Optional[str] = Header(None, include_in_schema=False),
):
    """
    Official Scanbase prices: price, market cap, and 1h/24h/7d change.
    USD comes from global exchanges only, INR from Indian exchanges only.
    Biggest coins first unless you sort differently.
    """
    require_key(x_api_key)
    cur = currency.strip().upper()
    if cur not in ("USD", "INR"):
        raise HTTPException(status_code=400, detail="currency must be usd or inr")
    sort_key = sort.strip().lower()
    if sort_key not in SORTS:
        raise HTTPException(status_code=400,
                            detail=f"sort must be one of: {', '.join(SORTS)}")
    if order.strip().lower() not in ("asc", "desc"):
        raise HTTPException(status_code=400, detail="order must be desc or asc")
    direction = order.strip().upper()
    # "rank" counts upwards (1 is best), so asc/desc read the natural way.
    order_sql = (f"{SORTS[sort_key]} {direction} NULLS LAST, "
                 "i.market_cap DESC NULLS LAST, i.volume_quote DESC NULLS LAST, i.base")

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
    def run_query():
        with engine.connect() as conn:
            total = conn.execute(text(f"SELECT count(*) {base_sql}"), params).scalar()
            rows = conn.execute(text(f"""
                SELECT i.*, c.slug, c.name, c.rank,
                       CASE WHEN i.market_cap IS NOT NULL THEN (
                           SELECT count(*) + 1 FROM index_latest x
                           WHERE x.currency = i.currency AND x.market_cap > i.market_cap
                       ) END AS market_cap_rank
                {base_sql}
                ORDER BY {order_sql}
                LIMIT :limit OFFSET :offset
            """), params).mappings().all()
        return total, rows

    # Only the query is cached. Ages are worked out below against the
    # real clock, so a cached answer can never claim to be fresher than
    # it is.
    total, rows = cached(
        f"prices:{cur}:{symbols}:{listed_only}:{sort_key}:{order}:{limit}:{offset}",
        run_query,
    )

    now = datetime.now(timezone.utc)
    return {
        "currency": cur,
        "total": total,
        "limit": limit,
        "offset": offset,
        "sort": sort_key,
        "order": order.strip().lower(),
        "prices": [
            {"symbol": r["base"], "coin_id": r["slug"], "name": r["name"],
             "rank": r["rank"], "market_cap_rank": r["market_cap_rank"],
             "logo_url": logo_url(r["base"]), **index_row_to_dict(r, now)}
            for r in rows
        ],
    }


@app.get("/v1/prices/{coin}", tags=["Prices"])
def get_price(coin: str, x_api_key: Optional[str] = Header(None, include_in_schema=False)):
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
        usd_inr_bank, bank_at = load_rate(conn)

    if not rows:
        raise HTTPException(status_code=404, detail=f"No official price for '{coin}'")

    now = datetime.now(timezone.utc)
    by_cur = {r["currency"]: index_row_to_dict(r, now) for r in rows}
    usd, inr = by_cur.get("USD"), by_cur.get("INR")
    # Two different questions, two different numbers.
    # 1. Are Indian exchanges dearer than global ones, once you are
    #    already holding USDT? Usually almost nothing.
    # 2. Is an Indian paying more than the plain dollar value of the
    #    coin at the bank rate? Usually a few percent, and that is the
    #    number that costs a buyer real money.
    premium = None
    if usd and inr and usdt_inr:
        premium = round((inr["price"] / (usd["price"] * usdt_inr) - 1) * 100, 3)
    bank_premium = None
    if usd and inr and usd_inr_bank:
        bank_premium = round((inr["price"] / (usd["price"] * usd_inr_bank) - 1) * 100, 3)

    return {
        "symbol": symbol,
        "coin_id": slug,
        "logo_url": logo_url(symbol),
        "usd": usd,
        "inr": inr,
        "usdt_inr": usdt_inr,
        "usd_inr_bank": usd_inr_bank,
        "usd_inr_bank_updated_at": bank_at.isoformat() if bank_at else None,
        "india_premium_pct": premium,
        "india_premium_vs_bank_pct": bank_premium,
    }


@app.get("/v1/candles/{coin}", tags=["Prices"])
def get_candles(
    coin: str,
    currency: str = Query("usd", description="usd or inr"),
    interval: str = Query("1h", description="1h (last 90 days) or 1d (all history)"),
    days: int = Query(7, ge=1, le=3650),
    x_api_key: Optional[str] = Header(None, include_in_schema=False),
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


@app.get("/v1/exchanges/{slug}", tags=["Exchanges"])
def exchange_detail(slug: str, x_api_key: Optional[str] = Header(None, include_in_schema=False)):
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



# ---------- the whole market in one answer ----------

@app.get("/v1/global", tags=["Prices"])
def global_stats(
    currency: str = Query("usd", description="usd or inr"),
    x_api_key: Optional[str] = Header(None, include_in_schema=False),
):
    """
    Market totals: combined market cap, trading volume across the
    exchanges we collect from, and Bitcoin's share.

    Market cap counts only coins whose circulating supply we hold, so
    it is the total of what we can actually measure rather than an
    estimate of the whole market.
    """
    require_key(x_api_key)
    cur = currency.strip().upper()
    if cur not in ("USD", "INR"):
        raise HTTPException(status_code=400, detail="currency must be usd or inr")

    return cached(f"global:{cur}", lambda: _global_stats(cur))


def _global_stats(cur):
    with engine.connect() as conn:
        totals = conn.execute(text("""
            SELECT count(*),
                   count(*) FILTER (WHERE market_cap IS NOT NULL),
                   SUM(market_cap), SUM(volume_quote), MAX(updated_at)
            FROM index_latest WHERE currency = :cur
        """), {"cur": cur}).first()
        btc = conn.execute(text(
            "SELECT market_cap FROM index_latest WHERE base = 'BTC' AND currency = :cur"
        ), {"cur": cur}).scalar()
        eth = conn.execute(text(
            "SELECT market_cap FROM index_latest WHERE base = 'ETH' AND currency = :cur"
        ), {"cur": cur}).scalar()
        exchanges = conn.execute(text(
            "SELECT count(*) FROM exchanges WHERE is_active = TRUE"
        )).scalar()
        usdt_inr = usdt_inr_rate(conn)
        usd_inr_bank, bank_at = load_rate(conn)

    total_cap = float(totals[2]) if totals[2] else None
    share = (lambda v: round(float(v) / total_cap * 100, 3)
             if v and total_cap else None)

    return {
        "currency": cur,
        "coins_priced": totals[0],
        "coins_with_market_cap": totals[1],
        "total_market_cap": total_cap,
        "total_volume_24h": float(totals[3]) if totals[3] else None,
        "btc_dominance_pct": share(btc),
        "eth_dominance_pct": share(eth),
        "exchanges_tracked": exchanges,
        "usdt_inr": usdt_inr,
        "usd_inr_bank": usd_inr_bank,
        "usdt_premium_vs_bank_pct": (
            round((usdt_inr / usd_inr_bank - 1) * 100, 3)
            if usdt_inr and usd_inr_bank else None
        ),
        "updated_at": totals[4].isoformat() if totals[4] else None,
        "bank_rate_updated_at": bank_at.isoformat() if bank_at else None,
    }



# ---------- front-page data ----------

_snapshot = {"at": None, "data": None}


@app.get("/v1/demo/snapshot", tags=["Service"])
def demo_snapshot():
    """
    A handful of live numbers for the front page. No key needed, because
    it is the same public market data anyone can see on the site.
    Cached for 30 seconds so a busy page cannot hammer the database.
    """
    now = datetime.now(timezone.utc)
    if _snapshot["at"] and (now - _snapshot["at"]).total_seconds() < 30:
        return _snapshot["data"]

    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT currency, price, sources, updated_at FROM index_latest WHERE base = 'BTC'"
        )).fetchall()
        coins = conn.execute(text(
            "SELECT count(*) FROM index_latest WHERE currency = 'USD'"
        )).scalar()
        exchanges = conn.execute(text(
            "SELECT count(*) FROM exchanges WHERE is_active = TRUE"
        )).scalar()
        usd_inr_bank, _ = load_rate(conn)

    by_cur = {r[0]: r for r in rows}
    usd = float(by_cur["USD"][1]) if "USD" in by_cur else None
    inr = float(by_cur["INR"][1]) if "INR" in by_cur else None
    fresh = by_cur.get("USD") or by_cur.get("INR")
    data = {
        "symbol": "BTC",
        "usd": usd,
        "inr": inr,
        "sources": by_cur["USD"][2] if "USD" in by_cur else None,
        "india_premium_vs_bank_pct": (
            round((inr / (usd * usd_inr_bank) - 1) * 100, 3)
            if usd and inr and usd_inr_bank else None
        ),
        "coins_priced": coins,
        "exchanges": exchanges,
        "age_seconds": age_in_seconds(fresh[3], now) if fresh else None,
    }
    _snapshot.update({"at": now, "data": data})
    return data



# ---------- what a trade really costs in India ----------

@app.get("/v1/cost/{coin}", tags=["India"])
def true_cost(
    coin: str,
    amount_inr: float = Query(100000, gt=0, description="Rupees you plan to spend or sell"),
    side: str = Query("buy", description="buy or sell"),
    x_api_key: Optional[str] = Header(None, include_in_schema=False),
):
    """
    The real cost of buying or selling a coin on each Indian exchange:
    the exchange's own price, its fee, GST on that fee, and TDS on a
    sale - measured against the coin's plain dollar value at the
    ordinary bank rate.

    Exchanges are ranked cheapest first. An exchange is listed but left
    out of the ranking when its price has gone stale, or when we have
    not verified its published fee - an admitted gap beats a guess, and
    a dead price beats neither.
    """
    require_key(x_api_key)
    if side not in ("buy", "sell"):
        raise HTTPException(status_code=400, detail="side must be buy or sell")

    now = datetime.now(timezone.utc)

    with engine.connect() as conn:
        slug, symbol = resolve_coin(conn, coin)
        name = conn.execute(text(
            "SELECT name FROM coins WHERE slug = :s"), {"s": slug}).scalar() if slug else None
        usd = conn.execute(text(
            "SELECT price FROM index_latest WHERE base = :b AND currency = 'USD'"
        ), {"b": symbol}).scalar()
        usd_inr_bank, bank_at = load_rate(conn)
        rows = conn.execute(text("""
            SELECT e.slug, e.name, p.price, p.collected_at,
                   f.fee_model, f.maker_pct, f.taker_pct, f.subscription_inr,
                   f.source_url, f.verified_on, f.notes
            FROM prices_latest p
            JOIN exchanges e ON e.id = p.exchange_id
            LEFT JOIN exchange_fees f ON f.slug = e.slug
            WHERE p.symbol_std = :pair AND e.country = 'IN' AND e.is_active = TRUE
        """), {"pair": f"{symbol}-INR"}).mappings().all()

    if not rows:
        raise HTTPException(status_code=404,
                            detail=f"No Indian exchange is quoting {symbol} in INR")

    fair_value = float(usd) * usd_inr_bank if usd and usd_inr_bank else None

    priced, unknown = [], []
    for r in rows:
        entry = {
            "exchange": r["slug"],
            "name": r["name"],
            "price": float(r["price"]),
            "age_seconds": age_in_seconds(r["collected_at"], now),
            "fee_source": r["source_url"],
            "fee_verified_on": r["verified_on"].isoformat() if r["verified_on"] else None,
            "fee_note": r["notes"],
        }
        # A pair an exchange has stopped quoting keeps its last price until
        # cleanup removes it. Ranking that would send a buyer to a price
        # that no longer exists, so anything stale is shown but not ranked.
        if entry["age_seconds"] is not None and entry["age_seconds"] > STALE_AFTER_SECONDS:
            entry.update({"fee_known": r["taker_pct"] is not None,
                          "ranked": False, "not_ranked_because": "price is stale"})
            unknown.append(entry)
            continue
        if r["taker_pct"] is None and r["fee_model"] != "subscription":
            entry.update({"fee_known": False, "ranked": False,
                          "not_ranked_because": "we have not verified this exchange's fee"})
            unknown.append(entry)
            continue
        cost = trade_cost(side, amount_inr, float(r["price"]), fair_value, dict(r),
                          TDS_PCT, GST_ON_FEE_PCT)
        stale = (r["verified_on"] is None
                 or (now.date() - r["verified_on"]).days > FEE_STALE_DAYS)
        entry.update(cost or {})
        entry.update({"fee_known": True, "ranked": True,
                      "fee_may_be_out_of_date": stale})
        priced.append(entry)

    # Cheapest first: least paid on a buy, most received on a sale.
    priced.sort(key=lambda e: (e["effective_price"] if side == "buy"
                               else -(e["rupees_received"] or 0)))

    return {
        "symbol": symbol,
        "coin_id": slug,
        "name": name,
        "side": side,
        "amount_inr": amount_inr,
        "usd_price": float(usd) if usd else None,
        "usd_inr_bank": usd_inr_bank,
        "bank_rate_updated_at": bank_at.isoformat() if bank_at else None,
        "fair_value_inr": fair_value,
        "tds_pct": TDS_PCT if side == "sell" else 0.0,
        "gst_on_fee_pct": GST_ON_FEE_PCT,
        "cheapest": priced[0]["exchange"] if priced else None,
        "exchanges": priced + unknown,
    }



# ---------- finding a coin ----------

@app.get("/v1/search", tags=["Coins"])
def search(
    q: str = Query(..., min_length=1, max_length=40, description="Symbol, name or slug"),
    limit: int = Query(10, ge=1, le=50),
    x_api_key: Optional[str] = Header(None, include_in_schema=False),
):
    """
    Find a coin by symbol, name or slug - what a search box needs.

    Coins with a page of their own come first, best-ranked first, and an
    exact symbol match always wins. Coins we price but have no page for
    are included after those, so a search never comes back empty just
    because we lack a description.

    Leveraged tokens (DOGE3L, BTCUP and the like) are never returned.
    They are derivatives that decay in value, they sit right next to the
    real coin in an exchange's list, and handing one to somebody
    searching for Dogecoin would be doing them harm.
    """
    require_key(x_api_key)
    term = q.strip()

    def build():
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT c.slug, UPPER(c.symbol) AS symbol, c.name, c.rank,
                       i.price AS usd_price, i.market_cap
                FROM coins c
                LEFT JOIN index_latest i
                       ON i.base = UPPER(c.symbol) AND i.currency = 'USD'
                WHERE c.is_active = TRUE
                  AND (UPPER(c.symbol) = UPPER(:exact)
                       OR c.slug ILIKE :like
                       OR c.name ILIKE :like
                       OR UPPER(c.symbol) LIKE UPPER(:prefix))
                ORDER BY (UPPER(c.symbol) = UPPER(:exact)) DESC,
                         (c.name ILIKE :prefix) DESC,
                         i.market_cap DESC NULLS LAST,
                         c.rank NULLS LAST
                LIMIT :limit
            """), {"exact": term, "like": f"%{term}%", "prefix": f"{term}%",
                   "limit": limit}).mappings().all()

            found = [{
                "symbol": r["symbol"], "coin_id": r["slug"], "name": r["name"],
                "rank": r["rank"], "logo_url": logo_url(r["symbol"]),
                "usd_price": num(r["usd_price"]), "market_cap": num(r["market_cap"]),
                "has_page": True,
            } for r in rows if not is_leveraged_token(r["symbol"])]

            # Room left over? Fill it with coins we price but cannot
            # describe, rather than returning a short list.
            if len(found) < limit:
                known = [f["symbol"] for f in found] or [""]
                extra = conn.execute(text("""
                    SELECT base, price FROM index_latest
                    WHERE currency = 'USD' AND base LIKE UPPER(:prefix)
                      AND base <> ALL(:known)
                    ORDER BY volume_quote DESC NULLS LAST
                    LIMIT :limit
                """), {"prefix": f"{term}%", "known": known,
                       "limit": limit - len(found)}).mappings().all()
                found += [{
                    "symbol": r["base"], "coin_id": None, "name": None, "rank": None,
                    "logo_url": logo_url(r["base"]), "usd_price": num(r["price"]),
                    "market_cap": None, "has_page": False,
                } for r in extra if not is_leveraged_token(r["base"])]
        return {"query": term, "count": len(found), "results": found}

    return cached(f"search:{term.lower()}:{limit}", build)


# ---------- where a coin can be bought ----------

@app.get("/v1/availability/{coin}", tags=["Exchanges"])
def availability(
    coin: str,
    all_pairs: bool = Query(False, alias="all",
                            description="Include every quote currency, not just the useful ones"),
    x_api_key: Optional[str] = Header(None, include_in_schema=False),
):
    """
    Every exchange currently quoting this coin, what it is priced
    against, and how fresh that price is - split into Indian and global.

    This is what tells a reader "you can buy this on these three Indian
    exchanges", and it is read from what we actually collected, not from
    a list somebody typed in.

    By default only rupee and dollar pairs are shown. Lira, real and yen
    pairs mean nothing to an Indian reader, and dead stablecoin pairs
    like BUSD and TUSD carry prices that drifted thousands of dollars
    from the market long ago. Pass `all=true` to see everything.
    """
    require_key(x_api_key)
    now = datetime.now(timezone.utc)

    def build():
        with engine.connect() as conn:
            slug, symbol = resolve_coin(conn, coin)
            rows = conn.execute(text("""
                SELECT e.slug, e.name, e.country, p.symbol, p.symbol_std,
                       p.price, p.volume_24h, p.collected_at
                FROM prices_latest p
                JOIN exchanges e ON e.id = p.exchange_id
                WHERE e.is_active = TRUE AND p.symbol_std LIKE :pair
                ORDER BY p.volume_24h DESC NULLS LAST
            """), {"pair": f"{symbol}-%"}).mappings().all()

        listings, india, globals_ = [], set(), set()
        for r in rows:
            age = age_in_seconds(r["collected_at"], now)
            quote = (r["symbol_std"] or "").split("-")[-1]
            if not all_pairs and quote not in USEFUL_QUOTES:
                continue
            entry = {
                "exchange": r["slug"], "name": r["name"],
                "region": "india" if r["country"] == "IN" else "global",
                "pair": r["symbol_std"], "exchange_symbol": r["symbol"],
                "quote": quote, "price": float(r["price"]),
                "volume_24h": num(r["volume_24h"]),
                "age_seconds": age,
                "is_stale": age is not None and age > STALE_AFTER_SECONDS,
            }
            listings.append(entry)
            if not entry["is_stale"]:
                (india if entry["region"] == "india" else globals_).add(r["slug"])

        return {
            "symbol": symbol,
            "coin_id": slug,
            "indian_exchanges": sorted(india),
            "global_exchanges": sorted(globals_),
            "listed_on": len(india) + len(globals_),
            "showing": "all pairs" if all_pairs else "INR and dollar pairs only",
            "buyable_with_inr": bool(india),
            "listings": listings,
        }

    return cached(f"avail:{coin.lower()}:{all_pairs}", build)
