-- Scanbase - API keys and usage tracking
-- Run this ONCE against the live database. Safe to run more than once.

-- Who is allowed to use the API, and how much.
--
-- We never store the raw key itself. We store a hash of it - a one-way
-- scramble. When someone sends us a key, we scramble theirs the same
-- way and compare. That means even if someone got into this table,
-- they could not read anyone's actual key out of it.
CREATE TABLE IF NOT EXISTS api_keys (
    id            SERIAL PRIMARY KEY,
    key_hash      TEXT UNIQUE NOT NULL,   -- scrambled key, never the real one
    name          TEXT NOT NULL,          -- who this key belongs to, e.g. "CoinScanner"
    is_active     BOOLEAN DEFAULT TRUE,   -- set false to switch a key off instantly
    rate_limit    INTEGER DEFAULT 1000,   -- max requests allowed per hour
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- A running count of how many requests each key made in each hour.
-- One row per key per hour, rather than one row per request - that
-- keeps this table small no matter how much traffic we get.
CREATE TABLE IF NOT EXISTS api_usage (
    id            BIGSERIAL PRIMARY KEY,
    api_key_id    INTEGER NOT NULL REFERENCES api_keys(id),
    hour_bucket   TIMESTAMPTZ NOT NULL,
    request_count INTEGER DEFAULT 0,
    UNIQUE (api_key_id, hour_bucket)
);

CREATE INDEX IF NOT EXISTS idx_api_usage_lookup
    ON api_usage (api_key_id, hour_bucket);
