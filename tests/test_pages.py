"""The front page and the reference page are built in code, so check they build."""

from serve.pages import landing_html, docs_html


def test_front_page_uses_the_real_address():
    html = landing_html("https://scanbase-api.up.railway.app")
    assert html.startswith("<!doctype html>")
    assert "https://scanbase-api.up.railway.app/v1/prices/bitcoin" in html
    assert "__BASE__" not in html and "__TOKENS__" not in html and "__FONTS__" not in html
    # the live board must ask the key-free endpoint, never a keyed one
    assert '/v1/demo/snapshot' in html
    assert "X-API-Key: YOUR_KEY" in html


def test_reference_page_points_at_our_own_schema():
    html = docs_html("/openapi.json")
    assert 'url: "/openapi.json"' in html
    assert "__OPENAPI__" not in html and "__TOKENS__" not in html
    assert "swagger-ui-bundle" in html


def test_pages_are_readable_on_a_phone():
    for html in (landing_html("https://x.test"), docs_html("/openapi.json")):
        assert 'name="viewport"' in html
