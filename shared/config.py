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
