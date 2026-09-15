"""
Scanbase - the API

This is the part that finally lets outside systems - including
CoinScanner - ask "what's the price of Bitcoin?" and get a real
answer back over the internet, instead of someone opening the
database by hand.

Nothing in here collects data. It only reads what the background
worker (run_forever.py) has already saved. Collection and serving
are two separate jobs, running as two separate services, so a
problem in one never breaks the other.

Run locally with:
    uvicorn api.main:app --reload

On Railway, this runs as its own service, separate from the worker.
"""

import sys
import os
from typing import Optional

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI, HTTPException
from sqlalchemy import text
from core.db import engine
from core.symbols import standardise

app = FastAPI(
    title="Scanbase API",
    description="Live and historical crypto prices, collected from multiple exchanges.",
    version="0.1.0",
)


@app.get("/v1/health")
def health():
    """
    A simple 'are you alive' check. Used by Railway and by anyone
    integrating with the API to confirm it's actually responding
    before trying anything more complicated.
    """
    return {"status": "ok"}


@app.get("/v1/exchanges")
def list_exchanges():
    """
    Returns every exchange we collect from, and whether each one is
    currently marked active. This lets a customer see, at a glance,
    which sources their data is coming from.
    """
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT slug, name, is_active FROM exchanges ORDER BY slug")
        ).fetchall()

    return [
        {"slug": row[0], "name": row[1], "is_active": row[2]}
        for row in rows
    ]


@app.get("/v1/ticker/{symbol}")
def get_ticker(symbol: str):
    """
    Returns the current price of one symbol from every exchange that
    has it.

    You can ask using any common spelling - "BTCUSDT", "BTC-USDT" or
    "BTC_USDT" all find the same coin, because we match on our own
    standardised form rather than on whatever each exchange happened
    to call it.
    """
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
        # A 404 tells the caller clearly "we don't have this symbol",
        # rather than silently returning an empty list that looks like
        # something went wrong.
        raise HTTPException(status_code=404, detail=f"No data found for symbol '{symbol}'")

    def maybe_float(value):
        return float(value) if value is not None else None

    return {
        "symbol": wanted,
        "exchanges": [
            {
                "exchange": row[0],
                "name": row[1],
                "exchange_symbol": row[2],  # what this exchange actually calls it
                "price": float(row[3]),
                "bid": maybe_float(row[4]),
                "ask": maybe_float(row[5]),
                "high_24h": maybe_float(row[6]),
                "low_24h": maybe_float(row[7]),
                "volume_24h": maybe_float(row[8]),
                "collected_at": row[9].isoformat(),
            }
            for row in rows
        ],
    }


@app.get("/v1/markets")
def list_markets(exchange: Optional[str] = None):
    """
    Returns every symbol currently tracked, optionally filtered to
    one exchange. This is how a caller discovers what's available
    before asking for specific prices.
    """
    with engine.connect() as conn:
        if exchange:
            rows = conn.execute(
                text("""
                    SELECT DISTINCT p.symbol, e.slug
                    FROM prices_latest p
                    JOIN exchanges e ON e.id = p.exchange_id
                    WHERE e.slug = :exchange
                    ORDER BY p.symbol
                """),
                {"exchange": exchange},
            ).fetchall()
        else:
            rows = conn.execute(
                text("""
                    SELECT DISTINCT p.symbol, e.slug
                    FROM prices_latest p
                    JOIN exchanges e ON e.id = p.exchange_id
                    ORDER BY p.symbol
                """)
            ).fetchall()

    return {"count": len(rows), "markets": [{"symbol": r[0], "exchange": r[1]} for r in rows]}
