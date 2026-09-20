"""The small response cache: fewer database trips, never a stale claim."""

import time
from serve import cache


def setup_function():
    cache.clear()


def test_the_same_question_is_only_asked_once():
    trips = []
    build = lambda: trips.append(1) or {"n": len(trips)}
    first = cache.cached("k", build)
    assert cache.cached("k", build) == first
    assert cache.cached("k", build) == first
    assert len(trips) == 1


def test_different_questions_are_kept_apart():
    cache.cached("a", lambda: "one")
    cache.cached("b", lambda: "two")
    assert cache.cached("a", lambda: "changed") == "one"
    assert cache.cached("b", lambda: "changed") == "two"


def test_an_answer_is_rebuilt_once_it_expires():
    trips = []
    build = lambda: trips.append(1) or len(trips)
    assert cache.cached("k", build, ttl=0.05) == 1
    time.sleep(0.06)
    assert cache.cached("k", build, ttl=0.05) == 2


def test_the_cache_cannot_grow_without_limit():
    for i in range(cache.MAX_ENTRIES + 20):
        cache.cached(f"k{i}", lambda: i)
    assert cache.stats()["entries"] <= cache.MAX_ENTRIES
