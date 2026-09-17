"""Checks stale-price correction, India premium and best price."""

from ingest.validate import pick_price, clean_prices
from serve.markets import compute_premium, premium_table, rank_best


# ---------- stale price correction ----------

def test_wazirx_real_case_uses_midpoint():
    # Real WazirX numbers: last trade Rs 1 below the current buy offer
    price, source = pick_price(7522957, 7522958, 7597560, None)
    assert source == "midpoint" and price == (7522958 + 7597560) / 2


def test_normal_price_kept():
    assert pick_price(100, 99, 101, None) == (100, "last_trade")
    assert pick_price(99, 99, 101, None) == (99, "last_trade")      # equal to bid is fine


def test_no_offers_keeps_last():
    assert pick_price(100, None, None, None) == (100, "last_trade")


def test_crossed_book_not_trusted():
    assert pick_price(100, 105, 101, None) == (100, "last_trade")


def test_exchange_midpoint_label_kept():
    assert pick_price(100, 99, 101, "midpoint") == (100, "midpoint")


def test_clean_prices_applies_correction():
    rows = clean_prices([{"symbol": "BTCINR", "price": "80", "bid": "99", "ask": "101"}])
    assert rows[0]["price"] == 100 and rows[0]["price_source"] == "midpoint"


# ---------- premium ----------

def row(ex, country, sym, price, bid=None, ask=None):
    return {"exchange": ex, "name": ex.title(), "country": country, "symbol_std": sym,
            "price": price, "bid": bid, "ask": ask, "price_source": "last_trade"}


ROWS = [
    row("coindcx", "IN", "BTC-INR", 7_700_000),
    row("zebpay", "IN", "BTC-INR", 7_800_000),
    row("coindcx", "IN", "USDT-INR", 100),
    row("wazirx", "IN", "USDT-INR", 98),
    row("binance", "GLOBAL", "BTC-USDT", 75_000),
    row("okx", "GLOBAL", "BTC-USDT", 76_000),
    row("okx", "GLOBAL", "ETH-USDT", 3000),          # no INR price -> not in table
    row("wazirx", "IN", "BTC-USDT", 90_000),         # Indian USDT price ignored for "global"
]


def test_premium_math():
    p = compute_premium("btc", ROWS)
    # India 7,750,000 ; global 75,500 USDT x 99 = 7,474,500 -> +3.686%
    assert p["india"]["price_inr"] == 7_750_000
    assert p["global"]["price_usdt"] == 75_500
    assert p["usdt_inr"]["rate"] == 99
    assert p["premium_pct"] == 3.686
    assert p["global"]["exchanges"] == ["binance", "okx"]


def test_premium_missing_data():
    assert compute_premium("ETH", ROWS) is None
    assert compute_premium("BTC", [r for r in ROWS if r["symbol_std"] != "USDT-INR"]) is None


def test_premium_table_filters():
    assert [p["base"] for p in premium_table(ROWS)] == ["BTC"]
    assert premium_table(ROWS, min_india=3) == []


# ---------- best price ----------

def test_best_uses_ask_to_buy_and_bid_to_sell():
    rows = [
        row("coindcx", "IN", "BTC-INR", 100, bid=99, ask=101),
        row("zebpay", "IN", "BTC-INR", 100, bid=100, ask=103),
        row("giottus", "IN", "BTC-INR", 98),               # no offers
    ]
    r = rank_best(rows)
    assert [b["exchange"] for b in r["buy"]] == ["giottus", "coindcx", "zebpay"]
    assert r["buy"][0]["uses"].startswith("price")
    assert [s["exchange"] for s in r["sell"]] == ["zebpay", "coindcx", "giottus"]
    assert r["summary"]["best_buy"] == "giottus"
    assert r["summary"]["buy_price_spread_pct"] == round((103 / 98 - 1) * 100, 3)


def test_median_has_no_float_noise():
    rows = [row("a", "IN", "BTC-INR", 7602883.1), row("b", "IN", "BTC-INR", 7602883.645),
            row("c", "IN", "USDT-INR", 99.51), row("d", "GLOBAL", "BTC-USDT", 76000)]
    p = compute_premium("BTC", rows)
    assert p["india"]["price_inr"] == 7602883.3725
