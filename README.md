# Scanbase

Internal name for **CoinScanner API** — collects live crypto prices from
multiple exchanges, cleans them into one standard format, stores them,
and serves them through an API. CoinScanner is its first customer.

## How the code is organised

The code follows the path the data takes: **GET → CHECK → STORE → ISSUE**.

```
scanbase/
├── ingest/                 GETTING + CHECKING data
│   ├── base.py             the template every exchange follows
│   ├── registry.py         finds every exchange file automatically
│   ├── exchanges/          one small file per exchange
│   │   ├── global: binance okx bybit mexc gateio kucoin
│   │   ├── India:  coindcx wazirx giottus zebpay
│   │   ├── _helpers.py     shared number clean-up
│   │   └── _template.py    copy this to add a new exchange
│   ├── symbols.py          BTCUSDT / BTC_USDT / BTC-USDT → BTC-USDT
│   ├── validate.py         throws away broken prices
│   ├── history_filter.py   which pairs are worth keeping in history
│   ├── pipeline.py         one round: get → check → store
│   └── worker.py           runs rounds forever (Railway service 1)
│
├── storage/                STORING data
│   ├── db.py               the only file that talks to the database
│   ├── retention.py        daily clean-up: old hourly → daily summary
│   └── migrations/         numbered SQL files, safe to re-run
│
├── serve/                  ISSUING data
│   ├── main.py             the API endpoints (Railway service 2)
│   ├── logos.py            logo links + generated placeholder
│   ├── markets.py          India premium + best price calculations
│   ├── coin_format.py      cleans coin info before sending
│   └── auth.py             API keys (stored hashed) + rate limits
│
├── shared/config.py        every setting in one place
├── scripts/                admin tools: migrate, run_once, create_key,
│                           db_size, cleanup
├── tests/                  offline tests — no internet or database needed
└── docs/ARCHITECTURE.md    diagram and design decisions
```

**Rule:** `ingest` never serves, `serve` never collects, and only
`storage/db.py` opens database connections.

## API

Interactive docs: `https://scanbase-api.up.railway.app/docs`

| Endpoint | Key? | What it returns |
|---|---|---|
| `GET /` | No | Front page: what the API does, with a live Bitcoin board |
| `GET /docs` | No | Interactive reference - authorize once, then run any request |
| `GET /v1/demo/snapshot` | No | The handful of numbers the front page shows |
| `GET /v1/health` | No | API and database are up |
| `GET /v1/prices?currency=usd\|inr&symbols=&listed_only=&sort=&order=` | Yes | **Official prices, market cap and 1h/24h/7d change** (paged, sortable) |
| `GET /v1/prices/{coin}` | Yes | Official USD + INR price, and both India premiums, for one coin |
| `GET /v1/global?currency=usd\|inr` | Yes | Market totals: combined market cap, volume, BTC and ETH share |
| `GET /v1/cost/{coin}?amount_inr=&side=buy\|sell` | Yes | **True cost**: every Indian exchange ranked by what a trade really costs |
| `GET /v1/candles/{coin}?currency=&interval=1h\|1d&days=` | Yes | Candles of the official price (listed coins) |
| `GET /v1/exchanges/{slug}` | Yes | One exchange: quality rating and daily stats |
| `GET /v1/exchanges` | Yes | Exchanges we collect from, with quality rating |
| `GET /v1/status` | Yes | Whether each exchange is working, last error |
| `GET /v1/ticker/{symbol}` | Yes | One pair on every exchange, with quality flags, exchange time, and the official price |
| `GET /v1/markets?exchange=&limit=&offset=` | Yes | Every tracked pair (paged) |
| `GET /v1/coins?search=&limit=&offset=` | Yes | Coin list with logo links |
| `GET /v1/coins/{slug or symbol}` | Yes | Full coin info + live USDT price and market cap |
| `GET /v1/logos/{symbol}` | No | Logo image (generated circle if none) — usable in `<img>` |
| `GET /v1/premium` | Yes | India premium for every INR coin |
| `GET /v1/premium/{base}` | Yes | India premium for one coin (e.g. BTC) |
| `GET /v1/best/{symbol}?country=IN\|GLOBAL` | Yes | Cheapest place to buy, best place to sell |
| `GET /v1/history/{symbol}?interval=hour\|day&days=7&exchange=` | Yes | Past prices: hourly (90 days) or daily open/high/low/close |

Keys go in the `X-API-Key` header. `401` = bad key, `429` = over hourly limit.

## Running locally

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env            # then put your DATABASE_URL in it

python3 -m pytest               # offline tests
python3 -m scripts.migrate      # create / update tables
python3 -m scripts.run_once     # one collection round (or: run_once binance)
python3 -m ingest.worker        # run forever
uvicorn serve.main:app --reload # API at http://localhost:8000/docs
python3 -m scripts.create_key "CoinScanner"
python3 -m scripts.db_size      # table sizes
python3 -m scripts.cleanup      # run history clean-up by hand
python3 -m scripts.import_coinscanner <cs .env> <logos folder>   # copy coin info + logos
python3 -m scripts.fetch_logos  # find real logos (Trust Wallet, then icons set); runs on your Mac
```

First time on a Mac: `bash setup_mac.sh <path to old folder>` does the
venv, install, copies `.env`, runs tests and shows DB size.

Always run commands from the project folder, using `python3 -m`.

## Adding an exchange

1. Copy `ingest/exchanges/_template.py` → `ingest/exchanges/kucoin.py`
2. Fill in `SLUG`, `NAME`, `URL`, `FIELDS` (and `extract()` if needed)
3. Add a sample reply for it in `tests/test_exchanges.py`, run `pytest`
4. `INSERT INTO exchanges (slug, name) VALUES ('kucoin', 'KuCoin');`
5. `python3 -m scripts.run_once kucoin` → deploy

No other file changes. The worker picks it up by itself.

## Storage: what is kept, and for how long

| Table | Holds | Growth |
|---|---|---|
| `prices_latest` | Every pair, current price | Fixed — overwritten each round |
| `prices_hourly` | Useful pairs only, last 90 days | Fixed window |
| `prices_daily` | Older history, 1 row per pair per day | Slow |

"Useful" = priced in USDT/USDC with at least $10,000 traded in 24h,
or any INR pair (`ingest/history_filter.py`). Every pair is still
available live. The worker runs the clean-up once a day.

## Settings

Set as variables on Railway (defaults in `shared/config.py`):

| Variable | Default | Meaning |
|---|---|---|
| `DATABASE_URL` | — | Required |
| `SECONDS_BETWEEN_RUNS` | 60 | Gap between collection rounds |
| `STALE_AFTER_SECONDS` | 300 | Price older than this is marked stale |
| `DEFAULT_TIMEOUT_SECONDS` | 15 | Wait for an exchange before giving up |
| `DEFAULT_RATE_LIMIT` | 1000 | Hourly requests for new keys |
| `HISTORY_QUOTES` | USDT,USDC,INR | Pairs in these currencies can enter history |
| `HISTORY_ALWAYS_KEEP_QUOTES` | INR | Kept regardless of volume |
| `MIN_HISTORY_VOLUME_USD` | 10000 | Minimum 24h dollar volume for history |
| `HOURLY_KEEP_DAYS` | 90 | Hourly rows older than this become daily |
| `CLEANUP_EVERY_HOURS` | 24 | How often the worker cleans up |
| `PUBLIC_BASE_URL` | https://scanbase-api.up.railway.app | Used to build logo links |

## Deployment (Railway)

Two services, same code, different start commands:

| Service | Start command |
|---|---|
| worker | `python3 -m ingest.worker` |
| api | `uvicorn serve.main:app --host 0.0.0.0 --port $PORT` |

Python is pinned to 3.11 via `.python-version`.

## Logos

Order of preference: Trust Wallet (MIT) → cryptocurrency-icons (CC0) →
CoinScanner copy → generated circle. `scripts/fetch_logos.py` runs on a
laptop, so fetching costs nothing on the server. Logos are served with a
7-day browser cache. Licences: see `THIRD_PARTY_NOTICES.md`.

## Official prices (how they are calculated)

Every collection round, the worker turns exchange prices into one
official price per coin:

1. **Two separate prices.** USD uses only global exchanges' USDT/USDC
   pairs. INR uses only Indian exchanges' INR pairs. Indian exchanges
   never move the USD price.
2. **Flags** on every exchange price: `wide_spread` (gap > 2%),
   `thin_volume` (< $1,000 traded in 24h), `no_volume`,
   `estimated_price` (midpoint, not a trade), `outlier`.
3. **Wide-gap prices are dropped** when at least two clean ones remain.
4. **Outliers are dropped**: with 3+ prices, a modified z-score on the
   median absolute deviation (cut-off 3.5); with fewer, anything more
   than 50% away from the previous official price.
5. **Volume-weighted average** of what is left. Prices without volume
   get the smallest known weight.
6. **Confidence**: high (3+ exchanges), medium (2), low (1).

Candles of the official price are built from these per-minute values
for listed coins: hourly for 90 days, then daily.

## Exchange quality rating (last 7 days)

Uptime 30%, accuracy vs official price 35% (outliers penalised),
tight buy/sell gaps 20%, real trades vs estimates 15%. Grades A/B/C/D.
More than 20% outlier prices, or an average gap over 5%, is always D.
Shown after 30+ rounds.

## Breakage detection

An exchange returning zero valid prices is recorded as a failure. One
returning less than half its usual pairs gets a warning in `/v1/status`.

## True dollar prices

A USDT is not exactly a dollar. It usually trades a little under, so
treating it as $1 makes every price slightly too high.

Each round we read the USDC-USDT pairs on the global exchanges and work
out what a USDT is really worth (USDC is the steadier of the two, so it
is our dollar). Every USDT price is then converted at that rate, and
USDT itself gets a dollar price of its own. A safety range of 0.9 to
1.1 catches bad data; outside it we fall back to exactly $1.

The difference is small, roughly 0.04%, and it is the difference
between matching the big aggregators and being quietly off.

## Market cap and ranking

Market cap is the official price times the circulating supply held in
the `coins` table. Coins with no supply figure return an empty market
cap rather than a guessed one, and `market_cap_rank` is worked out live
from the current numbers instead of an inherited ranking.

`/v1/prices` sorts by `market_cap`, `volume`, `price`, `change_1h`,
`change_24h`, `change_7d` or `rank`, ascending or descending. Biggest
first is the default.

## Price changes

`change_1h_pct`, `change_24h_pct` and `change_7d_pct` compare the price
now with the official-price candle from that long ago. If the candle at
that exact hour is missing (the worker was down), the nearest earlier
candle within 3 hours is used.

Changes exist only for coins with candles, which means listed coins,
and only for windows we actually have. A brand new install shows an
empty 7d change for a week. That is deliberate: an empty number is
honest, a made-up one is not.

## The two India premiums

`/v1/prices/{coin}` answers two different questions, because they have
very different answers:

| Field | Question | Typical |
|---|---|---|
| `india_premium_pct` | Are Indian exchanges dearer than global ones, for someone already holding USDT? | near zero |
| `india_premium_vs_bank_pct` | Is an Indian paying more than the plain dollar value of the coin at the bank rate? | a few percent |

The second one is the money question. Almost all of it sits in the
rupee-to-USDT step, not in the exchange's coin price. The bank rate
comes from a free currency service, refreshed every few hours, and is
never mixed into any crypto price.

## What a trade really costs in India

`/v1/cost/{coin}` answers the question the site exists for: if I spend
a lakh on this coin today, what do I actually get, and where should I
buy it?

Three things sit between a buyer and the coin's plain dollar value:

| | What it is | Roughly |
|---|---|---|
| Exchange price premium | The rupee price sitting above the bank-rate value, mostly the USDT gap | 3 to 4% |
| Fee plus GST | The exchange's own cut, plus 18% GST on that cut | 0 to 0.55% |
| TDS | 1% taken by law, on a sale only, never on a buy | 1% on sale |

Exchanges are ranked cheapest first, and the ranking can surprise: an
exchange quoting a higher price can still win because it charges no
per-trade fee, while the cheapest quote can lose on a fat percentage.

### Fees are hand-kept, and the API says so

Aggregator sites disagree with each other about Indian exchange fees,
so every rate in `exchange_fees` comes from the exchange's own page and
carries that URL and the date it was read. Two rules follow:

- an exchange with no verified fee is **listed but left out of the
  ranking** - an admitted gap beats a guessed number
- an exchange whose **price has gone stale** is also listed but not
  ranked, with `not_ranked_because` saying why. Sending a buyer to a
  price that no longer exists is worse than showing one fewer option
- a fee older than 180 days is flagged `fee_may_be_out_of_date`

Only the base retail tier is stored. Volume tiers change often and do
not apply to ordinary buyers.

To update a rate, edit the row and set `verified_on` to today.

## Pairs that quietly disappear

When an exchange stops quoting a pair, its last price used to sit in
`prices_latest` for ever, looking exactly like a live one. Giottus
dropped BTC-INR while its other pairs kept flowing, and the stale price
went unnoticed for two days.

Every pair still being quoted is stamped with the current round's time,
so any row left hours behind is one the exchange has stopped returning.
Those rows are deleted as part of the same save. `VANISHED_PAIR_HOURS`
(6 by default) is the grace period, long enough that a few failed
rounds cannot wipe good pairs.
