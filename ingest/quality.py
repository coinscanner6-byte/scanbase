"""
Turning many exchange prices into ONE trustworthy price per coin.

Method (the same idea the big aggregators publish):
  1. Flag each exchange price: wide buy/sell gap, thin volume, no volume.
  2. Drop prices with a wide gap when enough other prices exist.
  3. Drop outliers - modified z-score on the median absolute deviation
     (needs 3+ prices), but never a price within 2% of the middle one.
     With fewer prices, drop anything more than 50% away from the
     previous official price.
  4. Volume-weighted average of what is left.

Two separate official prices:
  USD - from GLOBAL exchanges' USDT/USDC pairs
  INR - from INDIAN exchanges' INR pairs
Indian exchanges never move the USD price (their prices carry the
India premium).

Pure functions - no internet, no database.
"""

from statistics import median

from shared.config import WIDE_SPREAD_PCT, THIN_VOLUME_USD, OUTLIER_Z, OUTLIER_MIN_PCT

USD_QUOTES = ("USDT", "USDC")
JUMP_LIMIT = 0.5          # 50% away from the previous official price


def split_pair(symbol_std):
    if not symbol_std or "-" not in symbol_std:
        return None, None
    return tuple(symbol_std.rsplit("-", 1))


def quote_to_usd(quote, usdt_inr):
    """How many US dollars one unit of the quote currency is worth."""
    if quote in USD_QUOTES or quote == "USD":
        return 1.0
    if quote == "INR" and usdt_inr:
        return 1.0 / usdt_inr
    return None


def price_flags(row, usdt_inr=None):
    """Quality flags for one exchange price (a cleaned row)."""
    flags = []
    bid, ask, price = row.get("bid"), row.get("ask"), row["price"]
    if bid and ask and 0 < bid <= ask:
        if (ask - bid) / ((ask + bid) / 2) * 100 > WIDE_SPREAD_PCT:
            flags.append("wide_spread")
    volume = row.get("volume_24h")
    if volume is None:
        flags.append("no_volume")
    else:
        _, quote = split_pair(row.get("symbol_std"))
        rate = quote_to_usd(quote, usdt_inr)
        if rate is not None and price * volume * rate < THIN_VOLUME_USD:
            flags.append("thin_volume")
    if row.get("price_source") == "midpoint":
        flags.append("estimated_price")
    return flags


def aggregate(points, previous=None):
    """
    points: [{"exchange", "price", "volume" (coin units or None), "flags"}]
    Returns None, or:
      {"price", "kept", "excluded": {exchange: reason}, "confidence",
       "volume_quote"}
    """
    if not points:
        return None
    excluded = {}
    pts = list(points)

    # Step 2: wide gaps out, if at least 2 clean prices remain.
    clean = [p for p in pts if "wide_spread" not in p.get("flags", ())]
    if len(clean) >= 2 and len(clean) < len(pts):
        for p in pts:
            if "wide_spread" in p.get("flags", ()):
                excluded[p["exchange"]] = "wide_spread"
        pts = clean

    # Step 3: outliers.
    if len(pts) >= 3:
        mid = median(p["price"] for p in pts)
        mad = median(abs(p["price"] - mid) for p in pts)
        keep = []
        for p in pts:
            gap_pct = abs(p["price"] - mid) / mid * 100 if mid > 0 else 0
            if gap_pct <= OUTLIER_MIN_PCT:
                is_out = False            # normal difference between exchanges
            elif mad > 0:
                is_out = abs(0.6745 * (p["price"] - mid) / mad) > OUTLIER_Z
            else:
                is_out = True             # most prices identical, this one is not
            if is_out:
                excluded[p["exchange"]] = "outlier"
            else:
                keep.append(p)
        pts = keep
    elif previous:
        keep = []
        for p in pts:
            if abs(p["price"] - previous) / previous > JUMP_LIMIT:
                excluded[p["exchange"]] = "outlier"
            else:
                keep.append(p)
        pts = keep

    if not pts:
        return None

    # Step 4: volume-weighted average. Weight = value traded (quote units).
    weights = [p["price"] * p["volume"] if p.get("volume") else None for p in pts]
    known = [w for w in weights if w]
    if known:
        fallback = min(known)                     # unknown volume counts little
        weights = [w if w else fallback for w in weights]
    else:
        weights = [1.0] * len(pts)
    total = sum(weights)
    price = sum(p["price"] * w for p, w in zip(pts, weights)) / total
    if not price > 0:
        return None

    n = len(pts)
    return {
        "price": price,       # never rounded - tiny tokens cost < 0.0000000001
        "kept": sorted(p["exchange"] for p in pts),
        "excluded": dict(sorted(excluded.items())),
        "confidence": "high" if n >= 3 else "medium" if n == 2 else "low",
        "volume_quote": round(sum(known), 2) if known else None,
    }


def group_key(row, country):
    """Which official price a row feeds: (base, 'USD'|'INR') or None."""
    base, quote = split_pair(row.get("symbol_std"))
    if not base:
        return None
    if country == "IN" and quote == "INR":
        return base, "INR"
    if country != "IN" and quote in USD_QUOTES:
        return base, "USD"
    return None


def build_indexes(round_rows, countries, previous=None):
    """
    round_rows: {exchange_slug: [cleaned rows]} from one collection round
    countries:  {exchange_slug: "IN" | "GLOBAL"}
    previous:   {(base, currency): last official price}

    Returns (indexes, stats, usdt_inr)
      indexes: {(base, currency): aggregate result}
      stats:   {exchange: {"pairs", "wide", "thin", "midpoint", "outliers",
                           "median_dev_pct"}}
    """
    previous = previous or {}

    # First the USDT-INR rate - needed to judge INR volumes in dollars.
    fx_points = [
        {"exchange": ex, "price": r["price"], "volume": r.get("volume_24h"), "flags": []}
        for ex, rows in round_rows.items() if countries.get(ex) == "IN"
        for r in rows if r.get("symbol_std") == "USDT-INR"
    ]
    fx = aggregate(fx_points, previous.get(("USDT", "INR")))
    usdt_inr = fx["price"] if fx else None

    groups, stats, row_flags = {}, {}, {}
    for ex, rows in round_rows.items():
        country = countries.get(ex, "GLOBAL")
        s = stats.setdefault(ex, {"pairs": 0, "wide": 0, "thin": 0,
                                  "midpoint": 0, "outliers": 0, "devs": []})
        for r in rows:
            flags = price_flags(r, usdt_inr)
            s["pairs"] += 1
            s["wide"] += "wide_spread" in flags
            s["thin"] += "thin_volume" in flags
            s["midpoint"] += "estimated_price" in flags
            key = group_key(r, country)
            if key:
                groups.setdefault(key, []).append({
                    "exchange": ex, "price": r["price"],
                    "volume": r.get("volume_24h"), "flags": flags,
                })

    indexes = {}
    for key, points in groups.items():
        # One exchange can list both USDT and USDC pairs: use its best-volume one.
        best = {}
        for p in points:
            cur = best.get(p["exchange"])
            if cur is None or (p["volume"] or 0) > (cur["volume"] or 0):
                best[p["exchange"]] = p
        result = aggregate(list(best.values()), previous.get(key))
        if not result or not result["price"] > 0:
            continue
        indexes[key] = result
        for ex, reason in result["excluded"].items():
            if reason == "outlier":
                stats[ex]["outliers"] += 1
        if len(result["kept"]) >= 2:
            for p in best.values():
                stats[p["exchange"]]["devs"].append(
                    abs(p["price"] - result["price"]) / result["price"] * 100)

    for s in stats.values():
        devs = s.pop("devs")
        s["median_dev_pct"] = round(median(devs), 4) if devs else None

    return indexes, stats, usdt_inr
