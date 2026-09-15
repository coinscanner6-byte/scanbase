-- Scanbase - add standardised symbol column
-- Run this ONCE against the live database. Safe to run more than once.

-- "symbol" keeps whatever the exchange actually called it (BTCUSDT,
-- BTC_USDT, etc) so we can always trace a row back to its source.
-- "symbol_std" is our own standard form (BTC-USDT) used for lookups
-- and for matching the same coin across different exchanges.

ALTER TABLE prices_latest
    ADD COLUMN IF NOT EXISTS symbol_std TEXT;

ALTER TABLE prices_hourly
    ADD COLUMN IF NOT EXISTS symbol_std TEXT;

-- An index makes looking up by the standard symbol fast, which matters
-- because that is now the main way the API searches.
CREATE INDEX IF NOT EXISTS idx_prices_latest_symbol_std
    ON prices_latest (symbol_std);

CREATE INDEX IF NOT EXISTS idx_prices_hourly_symbol_std
    ON prices_hourly (symbol_std);
