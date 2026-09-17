"""
Checks every exchange translates its reply correctly - using saved
sample replies (copied from real responses), so no internet or
database is needed.
"""

from ingest.registry import load_exchanges
from ingest.validate import clean_prices

SAMPLES = {
    "binance": [{"symbol": "BTCUSDT", "lastPrice": "65000.5", "bidPrice": "65000", "askPrice": "65001",
                 "highPrice": "66000", "lowPrice": "64000", "volume": "1234.5"}],
    "mexc": [{"symbol": "BTCUSDT", "lastPrice": "65000.5", "bidPrice": "65000", "askPrice": "65001",
              "highPrice": "66000", "lowPrice": "64000", "volume": "1234.5"}],
    "okx": {"code": "0", "data": [{"instId": "BTC-USDT", "last": "65000.5", "bidPx": "65000", "askPx": "65001",
                                   "high24h": "66000", "low24h": "64000", "vol24h": "1234.5"}]},
    "bybit": {"result": {"list": [{"symbol": "BTCUSDT", "lastPrice": "65000.5", "bid1Price": "65000",
                                   "ask1Price": "65001", "highPrice24h": "66000", "lowPrice24h": "64000",
                                   "volume24h": "1234.5"}]}},
    "gateio": [{"currency_pair": "BTC_USDT", "last": "65000.5", "highest_bid": "65000", "lowest_ask": "65001",
                "high_24h": "66000", "low_24h": "64000", "base_volume": "1234.5"}],
    "coindcx": [
        {"market": "BTCUSDT", "high": "76774.08", "low": "75064.82", "volume": "1089191577.03",
         "last_price": "76274.01", "bid": "76274.00", "ask": "76274.01", "timestamp": 1789645052},
        {"market": "BTCINR", "high": "7600000", "low": "7400000", "volume": "15000000",
         "last_price": "7500000", "bid": "7499000", "ask": "7501000", "timestamp": 1789645052},
    ],
    "wazirx": [{"symbol": "btcinr", "baseAsset": "btc", "quoteAsset": "inr", "openPrice": "7472865",
                "lowPrice": "7411201.0", "highPrice": "7597577.0", "lastPrice": "7522957.0",
                "volume": "0.63987", "bidPrice": "7522958.0", "askPrice": "7597560.0", "at": 1789645051000}],
    "giottus": {"market": {
        "BTC/INR": {"top_bid": "7500000 INR", "top_ask": "7520000 INR"},
        "WBTC/INR": {"top_bid": "7233411 INR", "top_ask": "7819926 INR"},
        "DEAD/INR": {"top_bid": "0 INR", "top_ask": "5 INR"},
    }},
    "zebpay": {"data": [{"symbol": "BTC-INR", "timestamp": 1789645054840, "high": "0", "low": "0",
                         "bid": "", "ask": "", "last": "7510000", "baseVolume": "0"}]},
    "kucoin": {"data": {"ticker": [{"symbol": "BTC-USDT", "buy": "76149.25", "sell": "76368.47",
                                    "high": "76721.13", "low": "75072.2", "vol": "12.5",
                                    "last": "76200"}]}},
}

ALL = {"binance", "okx", "bybit", "mexc", "gateio",
       "coindcx", "wazirx", "giottus", "zebpay", "kucoin"}


def parsed(slug):
    return load_exchanges()[slug].parse(SAMPLES[slug])


def test_all_exchanges_found():
    assert set(load_exchanges()) == ALL


def test_template_and_helpers_ignored():
    assert "newexchange" not in load_exchanges()
    assert "_helpers" not in load_exchanges()


def test_every_exchange_has_a_sample():
    assert set(load_exchanges()) == set(SAMPLES), "add a sample reply for the new exchange"


def test_every_exchange_gives_a_clean_price():
    for slug in load_exchanges():
        good = clean_prices(parsed(slug))
        assert good, slug
        assert all(r["price"] > 0 and "-" in r["symbol_std"] for r in good), slug


def test_original_five_unchanged():
    for slug in ("binance", "okx", "bybit", "mexc", "gateio"):
        row = parsed(slug)[0]
        assert (row["price"], row["bid"], row["ask"], row["volume_24h"]) == \
               ("65000.5", "65000", "65001", "1234.5"), slug


def test_empty_replies_do_not_crash():
    for slug, exchange in load_exchanges().items():
        empty = {} if isinstance(SAMPLES[slug], dict) else []
        assert exchange.parse(empty) == [], slug


def test_coindcx_inr_only_and_volume_in_coins():
    rows = parsed("coindcx")
    assert [r["symbol"] for r in rows] == ["BTCINR"]      # USDT mirror dropped
    assert rows[0]["volume_24h"] == 2.0                   # 15,000,000 INR / 7,500,000


def test_wazirx_symbol_from_assets():
    rows = clean_prices(parsed("wazirx"))
    assert rows[0]["symbol"] == "BTC-INR" and rows[0]["symbol_std"] == "BTC-INR"
    # the real sample's last price is below its own bid -> stale -> midpoint
    assert rows[0]["price_source"] == "midpoint"


def test_giottus_midpoint_and_wide_spread_skipped():
    rows = parsed("giottus")
    assert [r["symbol"] for r in rows] == ["BTC/INR"]     # WBTC (8% gap) and DEAD skipped
    assert rows[0]["price"] == 7510000
    cleaned = clean_prices(rows)[0]
    assert cleaned["symbol_std"] == "BTC-INR" and cleaned["price_source"] == "midpoint"


def test_zebpay_zeros_become_empty():
    row = parsed("zebpay")[0]
    assert row["price"] == "7510000"
    assert row["bid"] is None and row["high_24h"] is None and row["volume_24h"] is None


def test_kucoin_bid_ask():
    row = parsed("kucoin")[0]
    assert (row["bid"], row["ask"], row["volume_24h"]) == ("76149.25", "76368.47", "12.5")
