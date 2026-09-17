"""
Price comparisons across exchanges. Pure calculations - no database -
so they can be tested on their own.

Each "row" is a dict:
    {"exchange", "name", "country", "symbol_std", "price", "bid", "ask", "price_source"}
Only fresh (non-stale) rows should be passed in.
"""

from statistics import median


def split_pair(symbol_std):
    if not symbol_std or "-" not in symbol_std:
        return None, None
    base, quote = symbol_std.rsplit("-", 1)
    return base, quote


def _mid(values):
    """Middle value, rounded to 8 decimals so float noise doesn't show."""
    values = [v for v in values if v]
    return round(median(values), 8) if values else None


def compute_premium(base, rows):
    """
    How much more (or less) a coin costs in India than globally.

    India price  = middle value of INR prices on Indian exchanges.
    Global price = middle value of USDT prices on global exchanges.
    Conversion   = middle value of USDT-INR on Indian exchanges - the
                   rate an Indian trader actually gets when moving money
                   through USDT (not the bank USD/INR rate).

    premium_pct > 0 means the coin is dearer in India.
    Returns None if any of the three prices is missing.
    """
    base = base.upper()
    india = [r for r in rows if r["country"] == "IN" and r["symbol_std"] == f"{base}-INR"]
    world = [r for r in rows if r["country"] != "IN" and r["symbol_std"] == f"{base}-USDT"]
    fx = [r for r in rows if r["country"] == "IN" and r["symbol_std"] == "USDT-INR"]

    india_price = _mid(r["price"] for r in india)
    world_price = _mid(r["price"] for r in world)
    usdt_inr = _mid(r["price"] for r in fx)
    if not (india_price and world_price and usdt_inr):
        return None

    world_in_inr = world_price * usdt_inr
    return {
        "base": base,
        "premium_pct": round((india_price / world_in_inr - 1) * 100, 3),
        "india": {
            "price_inr": india_price,
            "exchanges": sorted(r["exchange"] for r in india),
        },
        "global": {
            "price_usdt": world_price,
            "price_inr": round(world_in_inr, 2),
            "exchanges": sorted(r["exchange"] for r in world),
        },
        "usdt_inr": {
            "rate": usdt_inr,
            "exchanges": sorted(r["exchange"] for r in fx),
        },
    }


def premium_table(rows, min_india=1, min_global=1):
    """compute_premium for every coin that has INR and USDT prices."""
    bases = {split_pair(r["symbol_std"])[0] for r in rows
             if split_pair(r["symbol_std"])[1] == "INR"}
    bases.discard("USDT")
    out = []
    for base in sorted(b for b in bases if b):
        p = compute_premium(base, rows)
        if p and len(p["india"]["exchanges"]) >= min_india \
                and len(p["global"]["exchanges"]) >= min_global:
            out.append(p)
    return out


def rank_best(rows):
    """
    Where to buy cheapest and sell highest for one pair.

    Buying costs the ASK (lowest seller); selling earns the BID (highest
    buyer). If an exchange doesn't send offers, its price is used and
    flagged, because the real cost may differ.
    """
    buy, sell = [], []
    for r in rows:
        base_info = {"exchange": r["exchange"], "name": r["name"], "country": r["country"]}
        if r.get("ask"):
            buy.append({**base_info, "price": r["ask"], "uses": "ask"})
        else:
            buy.append({**base_info, "price": r["price"], "uses": "price (no offer data)"})
        if r.get("bid"):
            sell.append({**base_info, "price": r["bid"], "uses": "bid"})
        else:
            sell.append({**base_info, "price": r["price"], "uses": "price (no offer data)"})

    buy.sort(key=lambda x: x["price"])
    sell.sort(key=lambda x: -x["price"])

    result = {"buy": buy, "sell": sell}
    if buy and sell:
        cheapest, dearest = buy[0]["price"], buy[-1]["price"]
        result["summary"] = {
            "best_buy": buy[0]["exchange"],
            "best_sell": sell[0]["exchange"],
            "buy_price_spread_pct": round((dearest / cheapest - 1) * 100, 3) if cheapest else None,
        }
    return result
