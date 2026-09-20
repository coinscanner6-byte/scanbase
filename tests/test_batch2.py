"""Checks the Batch 2 work: true dollar prices, market cap, changes, FX."""

from ingest.quality import usd_per_usdt, to_usd, build_indexes
from shared.calc import market_cap, CHANGE_WINDOWS


def row(sym, price, vol=10):
    return {"symbol_std": sym, "price": price, "volume_24h": vol, "bid": None, "ask": None}


# ---------- what a USDT is really worth ----------

def test_peg_read_from_usdc_pairs():
    rounds = {"binance": [row("USDC-USDT", 1.0004, 1e6)],
              "okx": [row("USDC-USDT", 1.0004, 5e5)]}
    value, used = usd_per_usdt(rounds, {})
    assert round(value, 6) == round(1 / 1.0004, 6)     # about 0.9996
    assert used == ["binance", "okx"]


def test_peg_falls_back_to_one_dollar():
    assert usd_per_usdt({}, {}) == (1.0, [])                        # pair missing
    broken = {"binance": [row("USDC-USDT", 2.0, 1e6)]}              # absurd
    assert usd_per_usdt(broken, {}) == (1.0, [])
    indian = {"coindcx": [row("USDC-USDT", 1.0004, 1e6)]}           # Indian prices ignored
    assert usd_per_usdt(indian, {"coindcx": "IN"}) == (1.0, [])


def test_to_usd_only_discounts_usdt():
    assert to_usd("USDT", 0.9996) == 0.9996
    assert to_usd("USDC", 0.9996) == 1.0


def test_usd_prices_are_true_dollars():
    rounds = {
        "binance": [row("BTC-USDT", 80500, 100), row("USDC-USDT", 1.0004, 1e6)],
        "okx": [row("BTC-USDT", 80500, 100)],
        "gateio": [row("BTC-USDT", 80500, 100)],
    }
    idx, _, _ = build_indexes(rounds, {})
    btc = idx[("BTC", "USD")]["price"]
    assert 80460 < btc < 80480                       # about 80,468, not 80,500
    # USDT gets its own dollar price, since no USDT-USDT pair exists.
    assert round(idx[("USDT", "USD")]["price"], 4) == 0.9996
    # USDC stays on the dollar.
    assert abs(idx[("USDC", "USD")]["price"] - 1) < 0.0001


def test_inr_prices_are_not_touched_by_the_peg():
    rounds = {
        "binance": [row("USDC-USDT", 1.0004, 1e6)],
        "coindcx": [row("BTC-INR", 8000000, 2), row("USDT-INR", 99.45, 1e6)],
        "zebpay": [row("BTC-INR", 8000000, 1)],
    }
    idx, _, usdt_inr = build_indexes(rounds, {"coindcx": "IN", "zebpay": "IN"})
    assert idx[("BTC", "INR")]["price"] == 8000000
    assert usdt_inr == 99.45


# ---------- market cap ----------

def test_market_cap():
    assert market_cap("BTC", 80000, {"BTC": 19_900_000}) == 1_592_000_000_000.00
    assert market_cap("BTC", 80000, {}) is None          # supply unknown
    assert market_cap("BTC", 80000, None) is None
    assert market_cap("X", 0, {"X": 100}) is None        # no price, no cap


# ---------- change windows ----------

def test_change_windows_are_the_usual_three():
    assert CHANGE_WINDOWS == {"change_1h": 1, "change_24h": 24, "change_7d": 168}


# ---------- bank rate ----------

def test_bank_rate_rejects_nonsense(monkeypatch):
    import storage.fx as fx

    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            pass

        def json(self):
            return self.payload

    monkeypatch.setattr(fx.httpx, "get", lambda *a, **k: FakeResponse({"rates": {"INR": 88.7}}))
    assert fx.fetch_usd_inr() == 88.7
    monkeypatch.setattr(fx.httpx, "get", lambda *a, **k: FakeResponse({"rates": {"INR": 0.011}}))
    assert fx.fetch_usd_inr() is None            # upside down, refuse it
    monkeypatch.setattr(fx.httpx, "get", lambda *a, **k: FakeResponse({"result": "error"}))
    assert fx.fetch_usd_inr() is None            # service changed shape
