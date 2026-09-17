-- Scanbase - daily summaries for old history
-- Run this ONCE against the live database. Safe to run more than once.

-- Hourly rows older than 90 days are squeezed into one row per pair
-- per day here, then the hourly rows are deleted. We keep the useful
-- shape of the day (open, high, low, close) at ~1/24th of the size.
CREATE TABLE IF NOT EXISTS prices_daily (
    exchange_id  INTEGER NOT NULL REFERENCES exchanges(id),
    symbol       TEXT NOT NULL,
    symbol_std   TEXT,
    day          DATE NOT NULL,
    open         NUMERIC(20, 8) NOT NULL,   -- first hourly price that day
    high         NUMERIC(20, 8) NOT NULL,
    low          NUMERIC(20, 8) NOT NULL,
    close        NUMERIC(20, 8) NOT NULL,   -- last hourly price that day
    avg_price    NUMERIC(20, 8) NOT NULL,
    volume_24h   NUMERIC(24, 8),            -- last reported 24h volume that day
    samples      INTEGER NOT NULL,          -- how many hourly rows went in
    PRIMARY KEY (exchange_id, symbol, day)
);

CREATE INDEX IF NOT EXISTS idx_prices_daily_symbol_std
    ON prices_daily (symbol_std, day);

-- Makes "find hourly rows older than 90 days" fast.
CREATE INDEX IF NOT EXISTS idx_prices_hourly_hour_bucket
    ON prices_hourly (hour_bucket);
