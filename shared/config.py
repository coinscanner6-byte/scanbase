"""
Every setting Scanbase uses, in one place.

Before this file existed, numbers like "wait 60 seconds" or "a price
is old after 5 minutes" were scattered inside different files. Now
they live here, so changing one never means hunting through the code.

Any setting can be overridden on Railway by adding a variable with the
same name - no code change needed.
"""

import os
from dotenv import load_dotenv

load_dotenv()  # reads the .env file on your Mac; Railway sets these itself


def _int(name, default):
    value = os.getenv(name)
    return int(value) if value else default


# Where the database lives. Required - nothing works without it.
DATABASE_URL = os.getenv("DATABASE_URL")

# How long the worker waits between collection rounds.
SECONDS_BETWEEN_RUNS = _int("SECONDS_BETWEEN_RUNS", 60)

# A price older than this is marked "stale" in API answers.
# Worker runs every 60s, so 5 minutes means several rounds were missed.
STALE_AFTER_SECONDS = _int("STALE_AFTER_SECONDS", 300)

# How long we wait for an exchange to answer before giving up.
DEFAULT_TIMEOUT_SECONDS = _int("DEFAULT_TIMEOUT_SECONDS", 15)

# Default hourly request limit for new API keys.
DEFAULT_RATE_LIMIT = _int("DEFAULT_RATE_LIMIT", 1000)

# ---------- history (prices_hourly) ----------

# Only pairs priced in these currencies are kept in hourly history.
# Everything is still available LIVE in prices_latest - this only
# decides what we keep forever.
HISTORY_QUOTES = [q.strip().upper() for q in
                  os.getenv("HISTORY_QUOTES", "USDT,USDC,INR").split(",") if q.strip()]

# Quote currencies where the pair is kept no matter how small its volume
# (INR pairs are few and matter most for CoinScanner).
HISTORY_ALWAYS_KEEP_QUOTES = [q.strip().upper() for q in
                              os.getenv("HISTORY_ALWAYS_KEEP_QUOTES", "INR").split(",") if q.strip()]

# A USDT/USDC pair must have traded at least this many dollars in 24h
# to be kept in history. Filters out thousands of dead junk pairs.
MIN_HISTORY_VOLUME_USD = _int("MIN_HISTORY_VOLUME_USD", 10000)

# Hourly rows older than this are summarised into one row per day,
# then deleted.
HOURLY_KEEP_DAYS = _int("HOURLY_KEEP_DAYS", 90)

# How often the worker runs that clean-up, in hours.
CLEANUP_EVERY_HOURS = _int("CLEANUP_EVERY_HOURS", 24)

# ---------- coin info ----------

# The API's public address, used to build full logo links.
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://scanbase-api.up.railway.app").rstrip("/")

# ---------- data quality (Batch 1) ----------

# A buy/sell gap wider than this (%) flags the price as "wide_spread".
WIDE_SPREAD_PCT = float(os.getenv("WIDE_SPREAD_PCT", "2"))

# Less than this traded in 24h (in US dollars) flags "thin_volume".
THIN_VOLUME_USD = _int("THIN_VOLUME_USD", 1000)

# Outlier cut-off (modified z-score). 3.5 is the standard value.
OUTLIER_Z = float(os.getenv("OUTLIER_Z", "3.5"))

# A price within this % of the middle price is never an outlier - normal
# differences between exchanges (Indian ones often differ by 1-2%).
OUTLIER_MIN_PCT = float(os.getenv("OUTLIER_MIN_PCT", "2"))

# If an exchange suddenly returns less than this share of its usual
# number of pairs, a "possible API change" warning is recorded.
BREAKAGE_DROP = float(os.getenv("BREAKAGE_DROP", "0.5"))

# Official-price candles are kept hourly for this many days, then daily.
CANDLE_HOURLY_KEEP_DAYS = _int("CANDLE_HOURLY_KEEP_DAYS", 90)

# ---------- market data (Batch 2) ----------

# USDT is not exactly one dollar. We work out its real value from
# USDC-USDT pairs and price everything in true dollars. Set to 0 to
# go back to treating USDT as exactly $1.
USE_STABLECOIN_PEG = os.getenv("USE_STABLECOIN_PEG", "1") not in ("0", "false", "False")

# A safety belt: if the worked-out USDT value falls outside this range,
# something is wrong with the data, so we use 1.0 instead.
PEG_MIN = float(os.getenv("PEG_MIN", "0.9"))
PEG_MAX = float(os.getenv("PEG_MAX", "1.1"))

# Ordinary bank USD-INR rate, refreshed this often (hours).
FIAT_REFRESH_HOURS = _int("FIAT_REFRESH_HOURS", 6)
FIAT_RATE_URL = os.getenv("FIAT_RATE_URL", "https://api.exchangerate-api.com/v4/latest/USD")

# If a candle is missing at the exact hour we want to compare against,
# look back at most this many hours for the nearest one.
CHANGE_LOOKBACK_HOURS = _int("CHANGE_LOOKBACK_HOURS", 3)

# ---------- Indian taxes and fees (Batch 3) ----------

# Set by law, not by any exchange. TDS is deducted when you SELL a coin,
# not when you buy. GST applies to the exchange's fee, not to the trade.
TDS_PCT = float(os.getenv("TDS_PCT", "1.0"))
GST_ON_FEE_PCT = float(os.getenv("GST_ON_FEE_PCT", "18.0"))

# Past this many days, a stored exchange fee is called approximate
# rather than presented as fact.
FEE_STALE_DAYS = _int("FEE_STALE_DAYS", 180)

# A pair missing from an exchange's response for longer than this is
# treated as delisted and removed from the live table. Long enough that
# a few failed rounds cannot wipe good pairs.
VANISHED_PAIR_HOURS = _int("VANISHED_PAIR_HOURS", 6)
