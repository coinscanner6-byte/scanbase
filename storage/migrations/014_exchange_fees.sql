-- Scanbase - Batch 3: what a trade really costs in India.
-- Run ONCE against the live database. Safe to run more than once.

CREATE TABLE IF NOT EXISTS exchange_fees (
    slug                 TEXT PRIMARY KEY,
    -- 'percentage' = a cut of every trade. 'subscription' = a flat
    -- monthly charge with no per-trade cut (WazirX ZERO works this way).
    fee_model            TEXT NOT NULL DEFAULT 'percentage',
    maker_pct            NUMERIC(10, 5),
    taker_pct            NUMERIC(10, 5),
    subscription_inr     NUMERIC(12, 2),   -- per month, where fee_model = subscription
    inr_withdrawal_flat  NUMERIC(12, 2),
    source_url           TEXT,
    -- When a human last read this off the exchange's own fee page.
    -- Old dates make the API call the answer approximate instead of
    -- quietly serving a number that may have changed.
    verified_on          DATE,
    notes                TEXT
);

-- Seeded from each exchange's published retail rate, read on 2026-09-20.
-- Volume tiers are deliberately ignored: ordinary buyers sit on the base
-- tier, and base rates change far less often than tier tables.
INSERT INTO exchange_fees
    (slug, fee_model, maker_pct, taker_pct, subscription_inr, source_url, verified_on, notes)
VALUES
    ('wazirx', 'subscription', 0, 0, 99,
     'https://wazirx.com/fees', DATE '2026-09-20',
     'WazirX ZERO: flat monthly charge plus GST, no per-trade cut. Pay-per-trade tier also exists.'),
    ('zebpay', 'percentage', 0.45, 0.45, NULL,
     'https://zebpay.com/fees', DATE '2026-09-20',
     'Lowest order-book tier. Quick Trade is dearer, around 0.5%.'),
    ('coindcx', 'percentage', 0.20, 0.20, NULL,
     'https://coindcx.com/fees', DATE '2026-09-20',
     'Base spot tier for INR pairs. Drops sharply at high 30-day volume.')
ON CONFLICT (slug) DO NOTHING;
