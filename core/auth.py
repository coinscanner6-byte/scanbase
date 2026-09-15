"""
Checking API keys and enforcing rate limits.

How a key works:
    1. We generate a random key and give it to the customer, once.
    2. We save only a scrambled version (a hash) in our database.
    3. When they send us their key, we scramble theirs and compare.

We never store the real key. If our database ever leaked, nobody could
read anyone's key out of it - they'd only see scrambled text.
"""

import hashlib
import secrets
from datetime import datetime, timezone

from sqlalchemy import text
from core.db import engine


def generate_key():
    """
    Creates a brand new random API key. Called once when adding a
    customer. The plain key is shown to them at that moment and never
    stored anywhere - only its hash goes into the database.
    """
    return "sb_" + secrets.token_urlsafe(32)


def hash_key(raw_key):
    """
    Scrambles a key the same way every time, so we can compare a key
    someone sends us against what we stored without ever knowing the
    real value.
    """
    return hashlib.sha256(raw_key.encode()).hexdigest()


def check_key(raw_key):
    """
    Checks whether a key is real, active, and still within its hourly
    limit.

    Returns a dict describing what happened:
        {"ok": True,  "key_id": 1, "name": "CoinScanner"}
        {"ok": False, "reason": "invalid"}       - key not found or switched off
        {"ok": False, "reason": "rate_limited"}  - key is real but over its limit

    We separate those two failures on purpose: "your key is wrong" and
    "you're sending too fast" are very different problems, and a caller
    needs to know which one they have.
    """
    if not raw_key:
        return {"ok": False, "reason": "invalid"}

    key_hash = hash_key(raw_key)
    hour_bucket = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)

    with engine.begin() as conn:
        row = conn.execute(
            text("""
                SELECT id, name, rate_limit
                FROM api_keys
                WHERE key_hash = :key_hash AND is_active = TRUE
            """),
            {"key_hash": key_hash},
        ).fetchone()

        if row is None:
            return {"ok": False, "reason": "invalid"}

        key_id, name, rate_limit = row[0], row[1], row[2]

        # Count this request, creating this hour's row if it doesn't
        # exist yet. Doing the count and the check in one database trip
        # keeps it accurate even with several requests arriving at once.
        usage = conn.execute(
            text("""
                INSERT INTO api_usage (api_key_id, hour_bucket, request_count)
                VALUES (:key_id, :hour_bucket, 1)
                ON CONFLICT (api_key_id, hour_bucket)
                DO UPDATE SET request_count = api_usage.request_count + 1
                RETURNING request_count
            """),
            {"key_id": key_id, "hour_bucket": hour_bucket},
        ).fetchone()

        request_count = usage[0]

        if request_count > rate_limit:
            return {"ok": False, "reason": "rate_limited"}

        return {"ok": True, "key_id": key_id, "name": name}
