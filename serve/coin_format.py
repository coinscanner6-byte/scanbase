"""Cleans coin info before it is sent out. No database needed."""


def public_description(desc):
    """Hides internal fields (e.g. draft_source) - only summary and sections go out."""
    if not isinstance(desc, dict):
        return desc
    return {k: v for k, v in desc.items() if k in ("summary", "sections")}


def clean_links(links):
    """Drops empty links like "telegram": "" and empty entries inside lists."""
    if not isinstance(links, dict):
        return links
    out = {}
    for key, value in links.items():
        if isinstance(value, list):
            value = [v for v in value if v]
        if value:
            out[key] = value
    return out
