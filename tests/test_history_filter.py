"""Checks which pairs are kept in permanent history."""

from ingest.history_filter import keep_in_history, quote_of


def row(sym, price, vol):
    return {"symbol_std": sym, "price": price, "volume_24h": vol}


def test_quote_of():
    assert quote_of("BTC-USDT") == "USDT"
    assert quote_of("WEIRDPAIR") is None


def test_busy_usdt_pair_kept():
    assert keep_in_history(row("BTC-USDT", 65000, 100))


def test_dead_usdt_pair_dropped():
    assert not keep_in_history(row("JUNK-USDT", 0.0001, 5000))   # $0.50 traded


def test_other_quotes_dropped():
    assert not keep_in_history(row("ETH-BTC", 0.05, 99999))
    assert not keep_in_history(row("BTC-EUR", 60000, 99999))
    assert not keep_in_history(row("WEIRDPAIR", 1, 99999))


def test_inr_always_kept():
    assert keep_in_history(row("BTC-INR", 5_000_000, 0))


def test_missing_volume_kept():
    assert keep_in_history(row("NEW-USDC", 1, None))
