-- Scanbase - where each live price came from
-- Run this ONCE against the live database. Safe to run more than once.
-- Must run BEFORE deploying the code that writes it.

-- "last_trade" = the exchange's last trade price
-- "midpoint"   = halfway between best buy and sell offer, used when the
--                exchange gives no trade price (Giottus) or its last
--                trade is out of date (outside the current offers)
ALTER TABLE prices_latest
    ADD COLUMN IF NOT EXISTS price_source TEXT DEFAULT 'last_trade';
