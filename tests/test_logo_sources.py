"""Checks where logos are looked up. No internet needed."""

from ingest.logo_sources import candidates, trustwallet_urls, icons_url, SOURCE_RANK
from shared.keccak import checksum_address, keccak256


def test_keccak_known_value():
    assert keccak256(b"").hex() == "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"


def test_checksum_official_example():
    assert checksum_address("0x5aaeb6053f3e94c9b9a09f33669435e7ef1beaed") == \
        "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed"
    assert checksum_address("not an address") is None
    assert checksum_address("0xZZ") is None


def test_native_coin_first():
    urls = trustwallet_urls("bitcoin", {})
    assert urls == ["https://raw.githubusercontent.com/trustwallet/assets/master/blockchains/bitcoin/info/logo.png"]


def test_token_uses_checksummed_address_and_ethereum_first():
    urls = trustwallet_urls("tether", {
        "tron": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
        "ethereum": "0xdac17f958d2ee523a2206206994597c13d831ec7",
        "unknown-chain": "0xabc",
    })
    assert urls[0].endswith("/ethereum/assets/0xdAC17F958D2ee523a2206206994597C13D831ec7/logo.png")
    assert urls[1].endswith("/tron/assets/TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t/logo.png")
    assert len(urls) == 2


def test_order_trustwallet_then_icons():
    c = candidates("USDT", "tether", {"ethereum": "0xdac17f958d2ee523a2206206994597c13d831ec7"})
    assert [s for s, _ in c] == ["trustwallet", "icons"]
    assert c[-1][1].endswith("/128/color/usdt.png")


def test_unlisted_symbol_only_icons():
    assert candidates("ABC", None, None) == [("icons", icons_url("ABC"))]
    assert icons_url("1INCH.E") is None


def test_rank_order():
    assert SOURCE_RANK["trustwallet"] > SOURCE_RANK["icons"] > SOURCE_RANK["coinscanner"]
