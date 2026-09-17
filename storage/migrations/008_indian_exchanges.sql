-- Scanbase - Indian exchanges + KuCoin
-- Run this ONCE against the live database. Safe to run more than once.
-- Must run BEFORE deploying the new exchange files.

-- Where each exchange is based. Lets us compare Indian vs global prices.
ALTER TABLE exchanges ADD COLUMN IF NOT EXISTS country TEXT DEFAULT 'GLOBAL';

INSERT INTO exchanges (slug, name, country) VALUES
    ('coindcx', 'CoinDCX', 'IN'),
    ('wazirx',  'WazirX',  'IN'),
    ('giottus', 'Giottus', 'IN'),
    ('zebpay',  'ZebPay',  'IN'),
    ('kucoin',  'KuCoin',  'GLOBAL')
ON CONFLICT (slug) DO UPDATE SET country = EXCLUDED.country;
