"""
Copies coin info and logos from CoinScanner into Scanbase.

- CoinScanner is only READ (read-only connection) - nothing changes there.
- Safe to run again any time: existing coins and logos are updated,
  new ones added. Nothing in Scanbase is deleted.

    python3 -m scripts.import_coinscanner /tmp/cs.env ~/Downloads/v5-live/static/logos

The first argument is a file containing CoinScanner's PUBLIC database
address as DATABASE_URL=... . Scanbase's own address comes from .env.
"""

import json
import sys
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import create_engine, text

from storage.db import engine as scanbase
from serve.logos import detect_content_type

COLUMNS = [
    "slug", "symbol", "name", "rank", "description", "links", "categories",
    "contract_addresses", "genesis_date", "max_supply", "total_supply",
    "circulating_supply", "ath_usd", "ath_date", "atl_usd", "atl_date",
    "is_active", "updated_at",
]
JSON_COLUMNS = {"description", "links", "categories", "contract_addresses"}
MAX_LOGO_BYTES = 2 * 1024 * 1024


def clean_contracts(value):
    """CoinScanner stores "no contract" as {"": ""} - turn that into {}."""
    if not isinstance(value, dict):
        return value
    return {k: v for k, v in value.items() if k and v}


def read_coinscanner(env_file):
    url = dotenv_values(Path(env_file).expanduser()).get("DATABASE_URL")
    if not url:
        sys.exit(f"No DATABASE_URL in {env_file}")
    source = create_engine(url.replace("postgres://", "postgresql://", 1))
    with source.connect() as conn:
        conn.execute(text("SET TRANSACTION READ ONLY"))
        rows = conn.execute(
            text(f"SELECT {', '.join(COLUMNS)} FROM coins ORDER BY rank NULLS LAST")
        ).mappings().all()
    source.dispose()
    return [dict(r) for r in rows]


def import_coins(rows):
    sql = text("""
        INSERT INTO coins (slug, symbol, name, rank, description, links, categories,
            contract_addresses, genesis_date, max_supply, total_supply,
            circulating_supply, ath_usd, ath_date, atl_usd, atl_date,
            is_active, source, source_updated_at, imported_at)
        VALUES (:slug, :symbol, :name, :rank,
            CAST(:description AS JSONB), CAST(:links AS JSONB),
            CAST(:categories AS JSONB), CAST(:contract_addresses AS JSONB),
            :genesis_date, :max_supply, :total_supply, :circulating_supply,
            :ath_usd, :ath_date, :atl_usd, :atl_date, :is_active,
            'coinscanner', :updated_at, NOW())
        ON CONFLICT (slug) DO UPDATE SET
            symbol = EXCLUDED.symbol, name = EXCLUDED.name, rank = EXCLUDED.rank,
            description = EXCLUDED.description, links = EXCLUDED.links,
            categories = EXCLUDED.categories,
            contract_addresses = EXCLUDED.contract_addresses,
            genesis_date = EXCLUDED.genesis_date, max_supply = EXCLUDED.max_supply,
            total_supply = EXCLUDED.total_supply,
            circulating_supply = EXCLUDED.circulating_supply,
            ath_usd = EXCLUDED.ath_usd, ath_date = EXCLUDED.ath_date,
            atl_usd = EXCLUDED.atl_usd, atl_date = EXCLUDED.atl_date,
            is_active = EXCLUDED.is_active,
            source_updated_at = EXCLUDED.source_updated_at,
            imported_at = NOW()
    """)
    params = []
    for r in rows:
        r = dict(r)
        r["contract_addresses"] = clean_contracts(r.get("contract_addresses"))
        r["symbol"] = (r["symbol"] or "").upper()
        for c in JSON_COLUMNS:
            r[c] = json.dumps(r[c]) if r.get(c) is not None else None
        params.append(r)
    with scanbase.begin() as conn:
        conn.execute(sql, params)
    return len(params)


def import_logos(logo_dir, rows):
    """
    Loads every image in the folder, keyed by UPPERCASE symbol.

    Every valid logo is kept - not only the 601 listed coins - because
    Scanbase shows live prices for thousands of pairs and the logo
    endpoint is looked up by symbol. File names are matched
    case-insensitively (doge.png == DOGE.png). Names that aren't a plain
    symbol (e.g. "1INCH.E", "APE-X") are skipped.
    """
    folder = Path(logo_dir).expanduser()
    if not folder.is_dir():
        sys.exit(f"Logo folder not found: {folder}")

    listed = {r["symbol"].upper() for r in rows if r.get("symbol")}
    loaded, skipped = {}, []

    for f in sorted(folder.iterdir()):
        if not f.is_file() or f.name.startswith("."):
            continue
        symbol = f.stem.upper()
        if not symbol.isalnum() or len(symbol) > 20:
            skipped.append(f"{f.name} (not a plain symbol)")
            continue
        data = f.read_bytes()
        if len(data) > MAX_LOGO_BYTES:
            skipped.append(f"{f.name} (too big)")
            continue
        ctype = detect_content_type(data)
        if not ctype:
            skipped.append(f"{f.name} (not a recognised image)")
            continue
        loaded[symbol] = {"symbol": symbol, "ct": ctype, "data": data, "bytes": len(data)}

    if loaded:
        with scanbase.begin() as conn:
            conn.execute(text("""
                INSERT INTO coin_logos (symbol, content_type, data, bytes, updated_at)
                VALUES (:symbol, :ct, :data, :bytes, NOW())
                ON CONFLICT (symbol) DO UPDATE SET
                    content_type = EXCLUDED.content_type, data = EXCLUDED.data,
                    bytes = EXCLUDED.bytes, updated_at = NOW()
            """), list(loaded.values()))

    listed_with_logo = len(listed & set(loaded))
    return len(loaded), listed_with_logo, len(listed) - listed_with_logo, skipped


def main():
    if len(sys.argv) < 3:
        sys.exit("Usage: python3 -m scripts.import_coinscanner <cs .env file> <logos folder>")

    print("Reading coins from CoinScanner (read-only)...")
    rows = read_coinscanner(sys.argv[1])
    print(f"  found {len(rows)} coins")

    print("Saving coins into Scanbase...")
    print(f"  saved {import_coins(rows)} coins")

    print("Saving logos into Scanbase...")
    loaded, listed_with_logo, missing, skipped = import_logos(sys.argv[2], rows)
    print(f"  saved {loaded} logos in total")
    print(f"  {listed_with_logo} of the listed coins have a logo")
    print(f"  {missing} listed coins have no logo file (they'll get a generated circle)")
    if skipped:
        print(f"  skipped {len(skipped)} files:")
        for s in skipped[:15]:
            print(f"    - {s}")
        if len(skipped) > 15:
            print(f"    ... and {len(skipped) - 15} more")

    print("Done.")


if __name__ == "__main__":
    main()
