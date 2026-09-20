"""The true-cost maths: exchange fee, GST on that fee, and TDS on a sale."""

import pytest
from shared.calc import trade_cost

FAIR = 7_720_000.0          # BTC at the plain bank rate
PRICE = 8_001_494.0         # what an Indian exchange actually quotes
PCT = {"fee_model": "percentage", "taker_pct": 0.2}
SUB = {"fee_model": "subscription", "taker_pct": 0, "subscription_inr": 99}


def test_buy_charges_fee_and_gst_but_never_tds():
    r = trade_cost("buy", 100000, PRICE, FAIR, PCT)
    assert r["fee_inr"] == 200.0                 # 0.2% of a lakh
    assert r["gst_inr"] == 36.0                  # 18% of the fee
    assert r["tds_inr"] == 0.0                   # TDS is a sale-side tax
    assert r["total_charges_inr"] == 236.0


def test_sell_also_loses_one_percent_to_tds():
    r = trade_cost("sell", 100000, PRICE, FAIR, PCT)
    assert r["tds_inr"] == 1000.0
    assert r["rupees_received"] == 100000 - 200 - 36 - 1000


def test_a_subscription_costs_nothing_per_trade():
    r = trade_cost("buy", 100000, PRICE, FAIR, SUB)
    assert r["fee_inr"] == 0.0 and r["gst_inr"] == 0.0
    assert r["monthly_subscription_inr"] == 99.0
    # cheaper than a percentage exchange at the same quoted price
    assert r["total_cost_pct"] < trade_cost("buy", 100000, PRICE, FAIR, PCT)["total_cost_pct"]


def test_the_cost_splits_into_price_and_charges():
    r = trade_cost("buy", 100000, PRICE, FAIR, PCT)
    assert round(r["exchange_price_premium_pct"], 2) == 3.65    # the USDT gap
    assert round(r["fees_and_tax_pct"], 3) == 0.237             # fee plus GST
    assert r["total_cost_pct"] > r["exchange_price_premium_pct"]


def test_a_cheaper_quote_wins_even_with_a_higher_fee():
    cheap_price = trade_cost("buy", 100000, 7_900_000.0, FAIR,
                             {"fee_model": "percentage", "taker_pct": 0.45})
    dear_price = trade_cost("buy", 100000, 8_001_494.0, FAIR, PCT)
    assert cheap_price["effective_price"] < dear_price["effective_price"]


@pytest.mark.parametrize("amount,price", [(0, PRICE), (100000, 0), (-5, PRICE)])
def test_nonsense_input_returns_nothing(amount, price):
    assert trade_cost("buy", amount, price, FAIR, PCT) is None
