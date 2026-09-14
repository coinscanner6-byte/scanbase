-- Scanbase - add bid/ask/volume/high/low columns
-- Run this ONCE against the live database. Safe to run more than once -
-- IF NOT EXISTS means it won't complain if a column is already there.

ALTER TABLE prices_latest
    ADD COLUMN IF NOT EXISTS bid NUMERIC(20, 8),
    ADD COLUMN IF NOT EXISTS ask NUMERIC(20, 8),
    ADD COLUMN IF NOT EXISTS high_24h NUMERIC(20, 8),
    ADD COLUMN IF NOT EXISTS low_24h NUMERIC(20, 8),
    ADD COLUMN IF NOT EXISTS volume_24h NUMERIC(24, 8);

ALTER TABLE prices_hourly
    ADD COLUMN IF NOT EXISTS bid NUMERIC(20, 8),
    ADD COLUMN IF NOT EXISTS ask NUMERIC(20, 8),
    ADD COLUMN IF NOT EXISTS high_24h NUMERIC(20, 8),
    ADD COLUMN IF NOT EXISTS low_24h NUMERIC(20, 8),
    ADD COLUMN IF NOT EXISTS volume_24h NUMERIC(24, 8);

-- These are allowed to be empty (NULL) on purpose. Not every exchange
-- response will always include every field, and a missing bid should
-- never stop us from saving the price we did get.
