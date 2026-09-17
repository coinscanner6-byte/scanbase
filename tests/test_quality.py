"""Checks the official price, quality flags, rating and timestamps."""

from datetime import datetime, timezone

from ingest.quality import aggregate, price_flags, build_indexes, group_key
from ingest.validate import to_time, clean_prices
from serve.quality_score import score_exchange


def pt(ex, price, volume=None, flags=()):
    return {"exchange": ex, "price": price, "volume": volume, "flags": list(flags)}


# ---------- official price ----------

def test_volume_weighted():
    r = aggregate([pt("a", 100, 3), pt("b", 110, 1)])
    # weights = value traded: 300 and 110
    assert abs(r["price"] - (100 * 300 + 110 * 110) / 410) < 1e-9
    assert r["confidence"] == "medium" and r["kept"] == ["a", "b"]


def test_outlier_removed_with_three_or_more():
    r = aggregate([pt("a", 100, 1), pt("b", 101, 1), pt("c", 99, 1), pt("bad", 150, 1)])
    assert r["excluded"] == {"bad": "outlier"}
    assert 99 <= r["price"] <= 101 and r["confidence"] == "high"
    r = aggregate([pt("a", 100, 1), pt("b", 100.5, 1), pt("c", 99.5, 1), pt("far", 103, 1)])
    assert r["excluded"] == {"far": "outlier"}              # ~2.7% away and statistically odd


def test_bitbns_style_bad_price_removed():
    # the real Bitbns case: 49,999 while the market was ~76,000
    r = aggregate([pt("a", 76000, 5), pt("b", 76100, 5), pt("c", 75950, 5), pt("bitbns", 49999, 1)])
    assert "bitbns" in r["excluded"]


def test_identical_prices_mad_zero():
    r = aggregate([pt("a", 1.0, 1), pt("b", 1.0, 1), pt("c", 1.0, 1), pt("d", 1.05, 1)])
    assert r["excluded"] == {"d": "outlier"}
    r = aggregate([pt("a", 1.0, 1), pt("b", 1.0, 1), pt("c", 1.0, 1), pt("d", 1.015, 1)])
    assert r["excluded"] == {}                      # 1.5% is a normal difference


def test_normal_indian_gap_is_not_an_outlier():
    # real-life shape: three Indian prices very close, WazirX 0.7% higher
    r = aggregate([pt("coindcx", 7500000, 1), pt("giottus", 7510000), pt("zebpay", 7510000, 1),
                   pt("wazirx", 7560259, 1)])
    assert r["excluded"] == {}


def test_few_prices_use_previous_to_catch_jumps():
    r = aggregate([pt("a", 100, 1), pt("b", 300, 1)], previous=100)
    assert r["kept"] == ["a"] and r["excluded"] == {"b": "outlier"}
    assert aggregate([pt("a", 300, 1)], previous=100) is None


def test_wide_spread_dropped_only_if_others_remain():
    r = aggregate([pt("a", 100, 1), pt("b", 101, 1), pt("g", 104, None, ["wide_spread"])])
    assert r["excluded"] == {"g": "wide_spread"}
    alone = aggregate([pt("g", 104, None, ["wide_spread"])])
    assert alone["kept"] == ["g"] and alone["confidence"] == "low"


def test_unknown_volume_counts_little():
    r = aggregate([pt("big", 100, 1000), pt("novol", 200)])
    # fallback weight = smallest known (100,000) -> equal weights here
    assert r["price"] == 150
    assert aggregate([pt("a", 10), pt("b", 20)])["price"] == 15   # no volumes: plain average


# ---------- flags ----------

def test_flags():
    row = {"symbol_std": "X-INR", "price": 100, "bid": 95, "ask": 105, "volume_24h": 5,
           "price_source": "midpoint"}
    assert price_flags(row, usdt_inr=100) == ["wide_spread", "thin_volume", "estimated_price"]
    ok = {"symbol_std": "BTC-USDT", "price": 76000, "bid": 75999, "ask": 76001, "volume_24h": 10}
    assert price_flags(ok) == []
    assert price_flags({"symbol_std": "BTC-USDT", "price": 1}) == ["no_volume"]
    # INR thin volume can't be judged without a USDT-INR rate
    assert "thin_volume" not in price_flags({"symbol_std": "X-INR", "price": 1, "volume_24h": 1})


# ---------- grouping ----------

def test_indian_exchanges_never_move_usd_price():
    assert group_key({"symbol_std": "BTC-USDT"}, "IN") is None
    assert group_key({"symbol_std": "BTC-INR"}, "IN") == ("BTC", "INR")
    assert group_key({"symbol_std": "BTC-USDT"}, "GLOBAL") == ("BTC", "USD")
    assert group_key({"symbol_std": "BTC-INR"}, "GLOBAL") is None
    assert group_key({"symbol_std": "ETH-BTC"}, "GLOBAL") is None


def row(sym, price, vol=10, bid=None, ask=None):
    return {"symbol_std": sym, "price": price, "volume_24h": vol, "bid": bid, "ask": ask}


def test_build_indexes():
    rounds = {
        "binance": [row("BTC-USDT", 76000), row("BTC-USDC", 75000, vol=1)],
        "okx": [row("BTC-USDT", 76100)],
        "kucoin": [row("BTC-USDT", 90000)],     # outlier
        "gate": [row("BTC-USDT", 75950)],
        "coindcx": [row("BTC-INR", 7_600_000, 2), row("USDT-INR", 100, 1e6), row("BTC-USDT", 1)],
        "zebpay": [row("BTC-INR", 7_650_000, 1), row("USDT-INR", 99, 1e5)],
    }
    countries = {"coindcx": "IN", "zebpay": "IN"}
    idx, stats, usdt_inr = build_indexes(rounds, countries)
    usd, inr = idx[("BTC", "USD")], idx[("BTC", "INR")]
    assert usd["kept"] == ["binance", "gate", "okx"] and usd["excluded"] == {"kucoin": "outlier"}
    assert 75950 <= usd["price"] <= 76100            # Binance's USDC pair ignored (lower volume)
    assert inr["kept"] == ["coindcx", "zebpay"]
    assert 99 < usdt_inr < 100
    assert ("USDT", "INR") in idx
    assert stats["kucoin"]["outliers"] == 1
    assert stats["coindcx"]["pairs"] == 3              # Indian USDT pair counted, not used
    assert stats["okx"]["median_dev_pct"] is not None


# ---------- rating ----------

def test_score():
    good = score_exchange({"rounds_ok": 1440, "rounds_failed": 0, "pairs_sum": 100000,
                           "wide_sum": 1000, "midpoint_sum": 0, "outlier_sum": 10,
                           "dev_sum": 144.0, "dev_n": 1440})
    assert good["grade"] == "A" and good["uptime_pct"] == 100
    bad = score_exchange({"rounds_ok": 500, "rounds_failed": 500, "pairs_sum": 9000,
                          "wide_sum": 8000, "midpoint_sum": 9000, "outlier_sum": 900,
                          "dev_sum": 3000.0, "dev_n": 1000})
    assert bad["grade"] == "D"
    assert score_exchange({"rounds_ok": 5, "rounds_failed": 0, "pairs_sum": 10}) is None


# ---------- timestamps ----------

def test_to_time_units():
    s = to_time(1789645052)                 # seconds (CoinDCX)
    ms = to_time(1789645051000)             # milliseconds (WazirX)
    us = to_time(1789645056352980)          # microseconds (Delta)
    assert s.year == ms.year == us.year == 2026
    assert to_time(None) is None and to_time("junk") is None
    assert to_time(0) is None                                   # 1970 - unrealistic
    assert to_time(datetime(2099, 1, 1, tzinfo=timezone.utc).timestamp()) is None


def test_clean_prices_keeps_exchange_time():
    r = clean_prices([{"symbol": "BTCINR", "price": "1", "exchange_time": 1789645052}])[0]
    assert r["exchange_time"].year == 2026


def test_score_accepts_database_decimals():
    from decimal import Decimal
    r = score_exchange({"rounds_ok": Decimal(40), "rounds_failed": Decimal(0), "pairs_sum": Decimal(400),
                        "wide_sum": Decimal(4), "midpoint_sum": Decimal(0), "outlier_sum": Decimal(0),
                        "dev_sum": 1.2, "dev_n": Decimal(40)})
    assert r["grade"] in "ABCD" and r["rounds"] == 40


def test_regularly_wrong_exchange_is_always_d():
    r = score_exchange({"rounds_ok": 100, "rounds_failed": 0, "pairs_sum": 100,
                        "wide_sum": 0, "midpoint_sum": 0, "outlier_sum": 100,
                        "dev_sum": 3000.0, "dev_n": 100})
    assert r["grade"] == "D"


def test_tiny_prices_are_not_rounded_to_zero():
    r = aggregate([pt("a", 3e-12, 1e15), pt("b", 3.2e-12, 1e15)])
    assert 3e-12 <= r["price"] <= 3.2e-12
    idx, stats, _ = build_indexes(
        {"x": [row("TINY-USDT", 3e-12, 1e15)], "y": [row("TINY-USDT", 3.1e-12, 1e15)]}, {})
    assert idx[("TINY", "USD")]["price"] > 0
    assert stats["x"]["median_dev_pct"] is not None
