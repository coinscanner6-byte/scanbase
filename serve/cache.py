"""
A small in-memory cache for the heaviest read endpoints.

No Redis, no extra service, no cost. Prices only change every few
minutes, so holding an answer for half a minute cannot make it
meaningfully staler than it already is, and it keeps repeated
identical requests off the database.

The cache lives inside one API process. Restart the service and it is
empty again, which is fine - it is a shock absorber, not storage.
"""

import threading
import time

TTL_SECONDS = 30
MAX_ENTRIES = 500

_store = {}
_lock = threading.Lock()


def cached(key, build, ttl=TTL_SECONDS):
    """Return a stored answer if it is fresh, otherwise build and keep it."""
    now = time.monotonic()
    with _lock:
        hit = _store.get(key)
        if hit and now - hit[0] < ttl:
            return hit[1]

    value = build()          # built outside the lock: a slow query must
                             # never block every other request

    with _lock:
        if len(_store) >= MAX_ENTRIES:
            # Cheap eviction: drop the oldest quarter rather than track
            # usage. This cache is a buffer, not a careful LRU.
            for old in sorted(_store, key=lambda k: _store[k][0])[:MAX_ENTRIES // 4]:
                _store.pop(old, None)
        _store[key] = (now, value)
    return value


def clear():
    with _lock:
        _store.clear()


def stats():
    with _lock:
        return {"entries": len(_store), "ttl_seconds": TTL_SECONDS}
