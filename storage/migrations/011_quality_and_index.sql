-- Scanbase - Batch 1: official prices, candles, exchange quality
-- Run this ONCE against the live database. Safe to run more than once.
-- Must run BEFORE deploying the Batch 1 code.

-- The exchange's own timestamp for each price (alongside ours).
ALTER TABLE prices_latest ADD COLUMN IF NOT EXISTS exchange_time TIMESTAMPTZ;

-- Non-fatal warnings, e.g. "far fewer pairs than usual".
ALTER TABLE exchange_status ADD COLUMN IF NOT EXISTS last_warning TEXT;
ALTER TABLE exchange_status ADD COLUMN IF NOT EXISTS last_warning_at TIMESTAMPTZ;

-- The official price per coin: one row per (coin, USD or INR).
CREATE TABLE IF NOT EXISTS index_latest (
    base          TEXT NOT NULL,            -- e.g. BTC
    currency      TEXT NOT NULL,            -- USD or INR
    price         NUMERIC(30, 12) NOT NULL,
    confidence    TEXT NOT NULL,            -- high / medium / low
    sources       INTEGER NOT NULL,         -- exchanges used
    kept          TEXT[] NOT NULL,
    excluded      JSONB,                    -- {exchange: reason}
    volume_quote  NUMERIC(30, 2),           -- 24h value traded, in USD or INR
    updated_at    TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (base, currency)
);

-- Official-price candles for listed coins: hourly (90 days) then daily.
CREATE TABLE IF NOT EXISTS index_candles_1h (
    base      TEXT NOT NULL,
    currency  TEXT NOT NULL,
    hour      TIMESTAMPTZ NOT NULL,
    open      NUMERIC(30, 12) NOT NULL,
    high      NUMERIC(30, 12) NOT NULL,
    low       NUMERIC(30, 12) NOT NULL,
    close     NUMERIC(30, 12) NOT NULL,
    samples   INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (base, currency, hour)
);
CREATE INDEX IF NOT EXISTS idx_index_candles_1h_hour ON index_candles_1h (hour);

CREATE TABLE IF NOT EXISTS index_candles_1d (
    base      TEXT NOT NULL,
    currency  TEXT NOT NULL,
    day       DATE NOT NULL,
    open      NUMERIC(30, 12) NOT NULL,
    high      NUMERIC(30, 12) NOT NULL,
    low       NUMERIC(30, 12) NOT NULL,
    close     NUMERIC(30, 12) NOT NULL,
    samples   INTEGER NOT NULL,
    PRIMARY KEY (base, currency, day)
);

-- Daily running totals per exchange, used for the quality rating.
CREATE TABLE IF NOT EXISTS exchange_daily_stats (
    exchange_id    INTEGER NOT NULL REFERENCES exchanges(id),
    day            DATE NOT NULL,
    rounds_ok      INTEGER NOT NULL DEFAULT 0,
    rounds_failed  INTEGER NOT NULL DEFAULT 0,
    pairs_sum      BIGINT NOT NULL DEFAULT 0,
    wide_sum       BIGINT NOT NULL DEFAULT 0,
    thin_sum       BIGINT NOT NULL DEFAULT 0,
    midpoint_sum   BIGINT NOT NULL DEFAULT 0,
    outlier_sum    BIGINT NOT NULL DEFAULT 0,
    dev_sum        DOUBLE PRECISION NOT NULL DEFAULT 0,
    dev_n          INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (exchange_id, day)
);
