-- Scanbase - coin information and logos
-- Run this ONCE against the live database. Safe to run more than once.

-- Descriptive info about each coin (name, description, links, supply...).
-- First filled by copying from CoinScanner (scripts/import_coinscanner.py).
-- "slug" is the unique id (e.g. "dogecoin"); symbols can be shared by
-- different coins, so the symbol is NOT unique here.
CREATE TABLE IF NOT EXISTS coins (
    slug                TEXT PRIMARY KEY,
    symbol              TEXT NOT NULL,
    name                TEXT NOT NULL,
    rank                INTEGER,
    description         JSONB,
    links               JSONB,
    categories          JSONB,
    contract_addresses  JSONB,
    genesis_date        DATE,
    max_supply          NUMERIC,
    total_supply        NUMERIC,
    circulating_supply  NUMERIC,
    ath_usd             NUMERIC,
    ath_date            DATE,
    atl_usd             NUMERIC,
    atl_date            DATE,
    is_active           BOOLEAN DEFAULT TRUE,
    source              TEXT DEFAULT 'coinscanner',
    source_updated_at   TIMESTAMPTZ,      -- when the source last changed it
    imported_at         TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_coins_symbol ON coins (UPPER(symbol));
CREATE INDEX IF NOT EXISTS idx_coins_rank ON coins (rank);

-- Logo images, one per symbol, stored in the database itself.
-- Railway servers don't keep files between deploys, so images live here.
CREATE TABLE IF NOT EXISTS coin_logos (
    symbol        TEXT PRIMARY KEY,       -- always uppercase, e.g. "BTC"
    content_type  TEXT NOT NULL,          -- image/png, image/svg+xml...
    data          BYTEA NOT NULL,
    bytes         INTEGER NOT NULL,
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);
