-- Scanbase - Batch 2: price changes, market cap, bank FX rate
-- Run this ONCE against the live database. Safe to run more than once.
-- Must run BEFORE deploying the Batch 2 code.

-- Percentage change of the official price over three windows, and the
-- market cap (official price x circulating supply). Filled by the worker.
ALTER TABLE index_latest ADD COLUMN IF NOT EXISTS change_1h   NUMERIC(20, 6);
ALTER TABLE index_latest ADD COLUMN IF NOT EXISTS change_24h  NUMERIC(20, 6);
ALTER TABLE index_latest ADD COLUMN IF NOT EXISTS change_7d   NUMERIC(20, 6);
ALTER TABLE index_latest ADD COLUMN IF NOT EXISTS market_cap  NUMERIC(40, 2);
ALTER TABLE index_latest ADD COLUMN IF NOT EXISTS changes_at  TIMESTAMPTZ;

-- Sorting a market list by size or by activity must not scan everything.
CREATE INDEX IF NOT EXISTS idx_index_latest_mcap
    ON index_latest (currency, market_cap DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_index_latest_volume
    ON index_latest (currency, volume_quote DESC NULLS LAST);

-- Ordinary currency rates from a bank/reference source, NOT from crypto
-- exchanges. Used to show what an Indian buyer pays above the bank rate.
CREATE TABLE IF NOT EXISTS fx_rates (
    base        TEXT NOT NULL,          -- e.g. USD
    quote       TEXT NOT NULL,          -- e.g. INR
    rate        NUMERIC(30, 10) NOT NULL,
    source      TEXT,
    updated_at  TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (base, quote)
);
