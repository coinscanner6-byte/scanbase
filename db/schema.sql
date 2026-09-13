-- Scanbase - starting tables
-- Run this once against your database to create the tables.

-- A list of every exchange we collect from.
-- We look prices up by pointing at a row in here, instead of
-- writing the exchange's name as plain text everywhere.
CREATE TABLE IF NOT EXISTS exchanges (
    id           SERIAL PRIMARY KEY,
    slug         TEXT UNIQUE NOT NULL,   -- short code, e.g. "binance"
    name         TEXT NOT NULL,           -- display name, e.g. "Binance"
    is_active    BOOLEAN DEFAULT TRUE
);

-- The current price of every coin, on every exchange.
-- Only ONE row per (exchange, coin) pair. New prices overwrite the old
-- one instead of piling up. This keeps the table small forever.
CREATE TABLE IF NOT EXISTS prices_latest (
    exchange_id  INTEGER NOT NULL REFERENCES exchanges(id),
    symbol       TEXT NOT NULL,           -- e.g. "BTCUSDT"
    price        NUMERIC(20, 8) NOT NULL,
    collected_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (exchange_id, symbol)
);

-- One row per coin, per exchange, per hour. This is our permanent
-- history. It grows slowly and on purpose - about 10MB a year.
CREATE TABLE IF NOT EXISTS prices_hourly (
    id           BIGSERIAL PRIMARY KEY,
    exchange_id  INTEGER NOT NULL REFERENCES exchanges(id),
    symbol       TEXT NOT NULL,
    price        NUMERIC(20, 8) NOT NULL,
    hour_bucket  TIMESTAMPTZ NOT NULL,
    UNIQUE (exchange_id, symbol, hour_bucket)
);

-- Add our five confirmed exchanges. Safe to run more than once.
INSERT INTO exchanges (slug, name) VALUES
    ('binance', 'Binance'),
    ('okx',     'OKX'),
    ('bybit',   'Bybit'),
    ('mexc',    'MEXC'),
    ('gateio',  'Gate.io')
ON CONFLICT (slug) DO NOTHING;
