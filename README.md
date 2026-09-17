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
| `GET /v1/health` | No | API and database are up |
| `GET /v1/exchanges` | Yes | Exchanges we collect from |
| `GET /v1/status` | Yes | Whether each exchange is working, last error |
| `GET /v1/ticker/{symbol}` | Yes | Price of one pair on every exchange, with age and `is_stale` |
| `GET /v1/markets?exchange=` | Yes | Every tracked pair |
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
