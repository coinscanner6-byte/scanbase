"""Checks symbol standardising and price validation."""

from ingest.symbols import standardise
from ingest.validate import clean_prices


def test_all_spellings_become_one():
    for raw in ("BTCUSDT", "BTC-USDT", "BTC_USDT", "btc/usdt", " btcusdt "):
        assert standardise(raw) == "BTC-USDT", raw


def test_longer_quote_wins():
    assert standardise("ETHUSDC") == "ETH-USDC"
    assert standardise("ETHBTC") == "ETH-BTC"


def test_unknown_left_alone():
    assert standardise("WEIRDPAIR") == "WEIRDPAIR"


def test_bad_prices_dropped_good_kept():
    raw = [
        {"symbol": "BTCUSDT", "price": "65000"},
        {"symbol": "ZERO", "price": "0"},
        {"symbol": "NEG", "price": "-1"},
        {"symbol": "TEXT", "price": "abc"},
        {"symbol": "HUGE", "price": "999999999999"},
        {"symbol": "", "price": "5"},
        {"symbol": "NOPRICE", "price": None},
    ]
    good = clean_prices(raw)
    assert [g["symbol"] for g in good] == ["BTCUSDT"]
    assert good[0]["symbol_std"] == "BTC-USDT"
    assert good[0]["price"] == 65000.0


def test_broken_extra_field_keeps_row():
    good = clean_prices([{"symbol": "BTCUSDT", "price": "1", "bid": "oops"}])
    assert len(good) == 1 and good[0]["bid"] is None
