-- Scanbase - where each logo came from
-- Run this ONCE against the live database. Safe to run more than once.

-- coinscanner  = copied from CoinScanner's files
-- icons        = cryptocurrency-icons set (public domain, CC0)
-- trustwallet  = Trust Wallet assets (MIT licence)
ALTER TABLE coin_logos ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'coinscanner';
ALTER TABLE coin_logos ADD COLUMN IF NOT EXISTS source_url TEXT;
