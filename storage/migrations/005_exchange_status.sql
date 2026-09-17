-- Scanbase - exchange health tracking
-- Run this ONCE against the live database. Safe to run more than once.

-- One row per exchange, updated by the worker every round.
-- This lets the API answer "is each exchange working right now?"
-- without anyone reading Railway logs.
CREATE TABLE IF NOT EXISTS exchange_status (
    exchange_id      INTEGER PRIMARY KEY REFERENCES exchanges(id),
    last_success_at  TIMESTAMPTZ,          -- last round that worked
    last_saved_count INTEGER,              -- how many prices that round saved
    last_error_at    TIMESTAMPTZ,          -- last round that failed
    last_error       TEXT,                 -- what went wrong (short)
    updated_at       TIMESTAMPTZ DEFAULT NOW()
);
