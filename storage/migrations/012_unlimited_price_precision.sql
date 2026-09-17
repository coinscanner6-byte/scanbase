-- Scanbase - store prices with unlimited decimal places
-- Run this ONCE against the live database. Safe to run more than once.
--
-- Until now prices kept 8 decimal places, so tokens cheaper than
-- 0.00000001 were saved as 0. Removing the limit is instant in Postgres
-- (no table rewrite).
--
-- If the tables are busy, give up after 10 seconds instead of waiting
-- and holding up the worker - just run the migration again.
SET lock_timeout = '10s';

ALTER TABLE prices_latest
    ALTER COLUMN price TYPE NUMERIC,
    ALTER COLUMN bid TYPE NUMERIC,
    ALTER COLUMN ask TYPE NUMERIC,
    ALTER COLUMN high_24h TYPE NUMERIC,
    ALTER COLUMN low_24h TYPE NUMERIC,
    ALTER COLUMN volume_24h TYPE NUMERIC;

ALTER TABLE prices_hourly
    ALTER COLUMN price TYPE NUMERIC,
    ALTER COLUMN bid TYPE NUMERIC,
    ALTER COLUMN ask TYPE NUMERIC,
    ALTER COLUMN high_24h TYPE NUMERIC,
    ALTER COLUMN low_24h TYPE NUMERIC,
    ALTER COLUMN volume_24h TYPE NUMERIC;

ALTER TABLE prices_daily
    ALTER COLUMN open TYPE NUMERIC,
    ALTER COLUMN high TYPE NUMERIC,
    ALTER COLUMN low TYPE NUMERIC,
    ALTER COLUMN close TYPE NUMERIC,
    ALTER COLUMN avg_price TYPE NUMERIC,
    ALTER COLUMN volume_24h TYPE NUMERIC;

ALTER TABLE index_latest
    ALTER COLUMN price TYPE NUMERIC,
    ALTER COLUMN volume_quote TYPE NUMERIC;

ALTER TABLE index_candles_1h
    ALTER COLUMN open TYPE NUMERIC,
    ALTER COLUMN high TYPE NUMERIC,
    ALTER COLUMN low TYPE NUMERIC,
    ALTER COLUMN close TYPE NUMERIC;

ALTER TABLE index_candles_1d
    ALTER COLUMN open TYPE NUMERIC,
    ALTER COLUMN high TYPE NUMERIC,
    ALTER COLUMN low TYPE NUMERIC,
    ALTER COLUMN close TYPE NUMERIC;

-- History rows wrongly saved as 0 are meaningless - remove them.
DELETE FROM prices_hourly WHERE price = 0;
DELETE FROM prices_latest WHERE price = 0;
