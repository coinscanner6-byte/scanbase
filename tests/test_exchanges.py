"""
Checks every exchange translates its reply correctly - using saved
sample replies, so no internet or database is needed.
"""

from ingest.registry import load_exchanges

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
}


def test_all_five_exchanges_found():
    assert set(load_exchanges()) == {"binance", "okx", "bybit", "mexc", "gateio"}


def test_template_is_ignored():
    assert "newexchange" not in load_exchanges()


def test_every_exchange_has_a_sample():
    assert set(load_exchanges()) == set(SAMPLES), "add a sample reply for the new exchange"


def test_every_exchange_parses_to_standard_shape():
    for slug, exchange in load_exchanges().items():
        rows = exchange.parse(SAMPLES[slug])
        assert len(rows) == 1, slug
        row = rows[0]
        assert row["price"] == "65000.5", slug
        assert row["bid"] == "65000", slug
        assert row["ask"] == "65001", slug
        assert row["volume_24h"] == "1234.5", slug


def test_empty_or_odd_replies_do_not_crash():
    for slug, exchange in load_exchanges().items():
        empty = {} if isinstance(SAMPLES[slug], dict) else []
        assert exchange.parse(empty) == [], slug
