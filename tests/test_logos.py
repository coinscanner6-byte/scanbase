"""Checks logo helpers."""

from serve.logos import placeholder_svg, detect_content_type, logo_url


def test_placeholder_same_colour_every_time():
    assert placeholder_svg("btc") == placeholder_svg("BTC")
    assert placeholder_svg("BTC") != placeholder_svg("ETH")
    assert ">BTC<" in placeholder_svg("btc")


def test_placeholder_matches_coinscanner_colour():
    # CoinScanner: hue = sum(ord(c)) * 37 % 360
    assert f"hsl({sum(map(ord, 'DOG')) * 37 % 360},55%,42%)" in placeholder_svg("DOGE")


def test_detect_types():
    assert detect_content_type(b"\x89PNG\r\n") == "image/png"
    assert detect_content_type(b"\xff\xd8\xff") == "image/jpeg"
    assert detect_content_type(b"<svg xmlns=...>") == "image/svg+xml"
    assert detect_content_type(b"hello") is None


def test_logo_url_uppercase():
    assert logo_url("doge").endswith("/v1/logos/DOGE")


def test_coin_output_cleaning():
    from serve.coin_format import public_description, clean_links
    assert public_description({"summary": "a", "sections": [], "draft_source": "x"}) == {"summary": "a", "sections": []}
    assert clean_links({"telegram": "", "web": ["x", ""], "gh": []}) == {"web": ["x"]}
