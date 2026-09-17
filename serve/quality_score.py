"""
Our own exchange rating, from data we collect ourselves (last 7 days).

  Uptime      30%  - share of collection rounds that worked
  Accuracy    35%  - how close its prices are to the official price,
                     minus a penalty for outliers
  Tight gaps  20%  - share of pairs WITHOUT a wide buy/sell gap
  Real trades 15%  - share of prices that are real trades, not estimates

Grade: A >= 85, B >= 70, C >= 50, D below. An exchange with more than
20% outlier prices, or an average gap over 5% from the official price,
is always D.
"""


def score_exchange(t):
    """t: summed daily stats. Returns dict, or None if not enough data."""
    # Database totals arrive as Decimal - convert everything to plain numbers.
    t = {k: float(v) if v is not None else None for k, v in t.items()}
    rounds = (t.get("rounds_ok") or 0) + (t.get("rounds_failed") or 0)
    pairs = t.get("pairs_sum") or 0
    if rounds < 30 or pairs == 0:
        return None

    uptime = (t.get("rounds_ok") or 0) / rounds
    avg_dev = (t["dev_sum"] / t["dev_n"]) if t.get("dev_n") else None
    outlier_ratio = (t.get("outlier_sum") or 0) / pairs
    accuracy = (max(0.0, 1 - avg_dev / 2) if avg_dev is not None else 0.5)
    accuracy *= 1 - min(outlier_ratio * 10, 1)
    tight = 1 - (t.get("wide_sum") or 0) / pairs
    real = 1 - (t.get("midpoint_sum") or 0) / pairs

    score = round(100 * (0.30 * uptime + 0.35 * accuracy + 0.20 * tight + 0.15 * real), 1)
    grade = "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 50 else "D"
    # Regularly wrong prices can't be outweighed by good uptime.
    if outlier_ratio > 0.2 or (avg_dev is not None and avg_dev > 5):
        grade = "D"
    return {
        "score": score,
        "grade": grade,
        "uptime_pct": round(uptime * 100, 2),
        "avg_deviation_pct": round(avg_dev, 4) if avg_dev is not None else None,
        "outlier_rate_pct": round(outlier_ratio * 100, 3),
        "wide_spread_pct": round((1 - tight) * 100, 2),
        "estimated_price_pct": round((1 - real) * 100, 2),
        "rounds": int(rounds),
    }
