"""
Logo helpers for the API.

A coin without an uploaded logo gets a generated coloured circle with
its symbol - the same design CoinScanner uses, with the same colour
per symbol, so both sites look identical.
"""

from shared.config import PUBLIC_BASE_URL


def logo_url(symbol):
    return f"{PUBLIC_BASE_URL}/v1/logos/{(symbol or '').upper()}"


def placeholder_svg(symbol):
    label = (symbol or "?").upper()[:3]
    hue = sum(ord(c) for c in label) * 37 % 360
    size = 11 if len(label) >= 3 else 13
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
        f'<circle cx="16" cy="16" r="16" fill="hsl({hue},55%,42%)"/>'
        '<text x="16" y="21" text-anchor="middle" '
        'font-family="-apple-system,Segoe UI,Roboto,sans-serif" '
        f'font-weight="700" font-size="{size}" fill="#fff">{label}</text>'
        '</svg>'
    )


def detect_content_type(data):
    """Works out the image type from the file's first bytes, not its name."""
    if data.startswith(b"\x89PNG"):
        return "image/png"
    if data.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data.startswith(b"GIF8"):
        return "image/gif"
    head = data[:300].lstrip().lower()
    if head.startswith(b"<svg") or head.startswith(b"<?xml"):
        return "image/svg+xml"
    return None
