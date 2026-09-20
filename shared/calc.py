"""
Small market calculations with no database and no internet, so they
can be tested on their own and run anywhere.
"""

# How far back each change window looks, in hours.
CHANGE_WINDOWS = {"change_1h": 1, "change_24h": 24, "change_7d": 24 * 7}


def market_cap(base, price, supplies):
    """
    Price x circulating supply - the usual way every market list is
    ordered. Returns None when we do not know the supply, because an
    invented market cap is worse than an empty one.
    """
    supply = (supplies or {}).get(base)
    if not supply or not price:
        return None
    return round(price * supply, 2)


def _pct(value, base):
    return round((value / base - 1) * 100, 4) if base else None


def trade_cost(side, amount_inr, exchange_price, fair_value, fee,
               tds_pct=1.0, gst_on_fee_pct=18.0):
    """
    What a trade on one Indian exchange really costs, in rupees.

    side          "buy"  - you spend amount_inr and receive coin
                  "sell" - you sell coin worth amount_inr and receive rupees
    exchange_price  that exchange's own live INR price for the coin
    fair_value      the coin's plain dollar value at the bank rate, in rupees
    fee             row from exchange_fees, as a dict

    The three things that make an Indian trade dearer than the coin's
    plain value, kept separate so a user can see which one is hurting:
      1. the exchange's rupee price sitting above the bank-rate value
      2. the exchange's own fee, plus GST on that fee
      3. TDS, which the law takes on a sale only

    A monthly subscription (WazirX ZERO) charges nothing per trade, so
    the per-trade fee is zero and the monthly amount is reported
    separately - spreading it over trades would need to guess how often
    somebody trades, and a guess does not belong in a cost figure.
    """
    if not amount_inr or not exchange_price or amount_inr <= 0 or exchange_price <= 0:
        return None

    per_trade_pct = float(fee.get("taker_pct") or 0)
    if (fee.get("fee_model") or "percentage") == "subscription":
        per_trade_pct = 0.0

    fee_inr = round(amount_inr * per_trade_pct / 100, 2)
    gst_inr = round(fee_inr * gst_on_fee_pct / 100, 2)

    if side == "sell":
        tds_inr = round(amount_inr * tds_pct / 100, 2)
        quantity = amount_inr / exchange_price
        received = amount_inr - fee_inr - gst_inr - tds_inr
        effective_price = received / quantity
    else:
        tds_inr = 0.0
        quantity = (amount_inr - fee_inr - gst_inr) / exchange_price
        received = None
        effective_price = amount_inr / quantity

    return {
        "side": side,
        "amount_inr": round(amount_inr, 2),
        "exchange_price": exchange_price,
        "quantity": quantity,
        "fee_inr": fee_inr,
        "gst_inr": gst_inr,
        "tds_inr": tds_inr,
        "total_charges_inr": round(fee_inr + gst_inr + tds_inr, 2),
        "rupees_received": round(received, 2) if received is not None else None,
        "effective_price": effective_price,
        # Where the cost comes from, in percent.
        "exchange_price_premium_pct": _pct(exchange_price, fair_value),
        "fees_and_tax_pct": abs(_pct(effective_price, exchange_price) or 0),
        "total_cost_pct": (
            _pct(effective_price, fair_value) if side == "buy"
            else (_pct(fair_value, effective_price) if effective_price else None)
        ),
        "fee_model": fee.get("fee_model") or "percentage",
        "monthly_subscription_inr": (
            float(fee["subscription_inr"])
            if fee.get("fee_model") == "subscription" and fee.get("subscription_inr")
            else None
        ),
    }
