"""
Finds real logos for coins that don't have a good one yet.

Runs on YOUR Mac - costs nothing on the server. Safe to run again any
time; it only fills gaps and upgrades to a better source.

    python3 -m scripts.fetch_logos                 everything
    python3 -m scripts.fetch_logos --limit 30      quick test on 30 symbols
    python3 -m scripts.fetch_logos --listed-only   only the 601 listed coins

Order of preference (a logo is only replaced by a better one):
    trustwallet  >  icons  >  coinscanner copy  >  generated circle

Which symbols:
  1. Listed coins (with their contract addresses) - best-ranked coin
     wins when two coins share a symbol.
  2. Every other coin that has a live price on any exchange - these
     can only be matched by symbol (icons set).
"""

import sys
from concurrent.futures import ThreadPoolExecutor

import httpx
from sqlalchemy import text

from ingest.logo_sources import SOURCE_RANK, candidates
from serve.logos import detect_content_type
from storage.db import engine

WORKERS = 8
MAX_BYTES = 2 * 1024 * 1024
HEADERS = {"User-Agent": "Mozilla/5.0 (Scanbase logo fetch)"}


def load_targets(listed_only):
    with engine.connect() as conn:
        existing = dict(conn.execute(text("SELECT symbol, source FROM coin_logos")).fetchall())
        coins = conn.execute(text("""
            SELECT UPPER(symbol), slug, contract_addresses
            FROM coins WHERE is_active = TRUE
            ORDER BY rank NULLS LAST
        """)).fetchall()
        traded = [] if listed_only else conn.execute(text("""
            SELECT DISTINCT split_part(symbol_std, '-', 1) FROM prices_latest
            WHERE symbol_std LIKE '%-%'
        """)).scalars().all()

    targets = {}
    for symbol, slug, contracts in coins:
        if symbol and symbol not in targets:          # best-ranked coin wins
            targets[symbol] = {"slug": slug, "contracts": contracts}
    for symbol in traded:
        s = (symbol or "").upper()
        if s and s.isalnum() and len(s) <= 20 and s not in targets:
            targets[s] = {"slug": None, "contracts": None}

    # Skip symbols that already have the best possible source.
    best = max(SOURCE_RANK.values())
    return {s: t for s, t in targets.items()
            if SOURCE_RANK.get(existing.get(s), 0) < best}, existing


def try_symbol(client, symbol, target, current_rank):
    for source, url in candidates(symbol, target["slug"], target["contracts"]):
        if SOURCE_RANK[source] <= current_rank:
            break                                     # nothing better left to find
        try:
            r = client.get(url)
        except httpx.HTTPError:
            continue
        if r.status_code != 200 or not r.content or len(r.content) > MAX_BYTES:
            continue
        ctype = detect_content_type(r.content)
        if ctype:
            return {"symbol": symbol, "ct": ctype, "data": r.content,
                    "bytes": len(r.content), "source": source, "url": url}
    return None


def save(found):
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO coin_logos (symbol, content_type, data, bytes, source, source_url, updated_at)
            VALUES (:symbol, :ct, :data, :bytes, :source, :url, NOW())
            ON CONFLICT (symbol) DO UPDATE SET
                content_type = EXCLUDED.content_type, data = EXCLUDED.data,
                bytes = EXCLUDED.bytes, source = EXCLUDED.source,
                source_url = EXCLUDED.source_url, updated_at = NOW()
        """), found)


def main():
    listed_only = "--listed-only" in sys.argv
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])

    targets, existing = load_targets(listed_only)
    items = sorted(targets.items())[:limit] if limit else sorted(targets.items())
    print(f"Checking {len(items)} symbols (already have a logo: {len(existing)})...")

    found, done = [], 0
    with httpx.Client(timeout=15, headers=HEADERS, follow_redirects=True) as client, \
            ThreadPoolExecutor(WORKERS) as pool:
        jobs = [pool.submit(try_symbol, client, s, t, SOURCE_RANK.get(existing.get(s), 0))
                for s, t in items]
        for job in jobs:
            result = job.result()
            done += 1
            if result:
                found.append(result)
                if len(found) % 100 == 0:
                    save(found[-100:])
            if done % 250 == 0:
                print(f"  checked {done}/{len(items)}, found {len(found)}")
        leftover = len(found) % 100
        if leftover:
            save(found[-leftover:])

    by_source = {}
    for f in found:
        key = f"{f['source']} ({'upgraded' if f['symbol'] in existing else 'new'})"
        by_source[key] = by_source.get(key, 0) + 1
    print("\nDone.")
    for k, v in sorted(by_source.items()):
        print(f"  {k}: {v}")
    got = {f["symbol"] for f in found}
    kept = sum(1 for sym, _ in items if sym not in got and sym in existing)
    circle = sum(1 for sym, _ in items if sym not in got and sym not in existing)
    print(f"  no better logo found, kept the existing one: {kept}")
    print(f"  still a generated circle: {circle}")


if __name__ == "__main__":
    main()
